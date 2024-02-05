import datetime
import hashlib
import io
import os
import shutil
import tempfile
import zipfile
from collections.abc import Mapping, Iterable
from typing import List, Optional

from beanie import PydanticObjectId
from beanie.operators import Or
from beanie.odm.operators.update.general import Inc
from bson import ObjectId
from bson import json_util
from elasticsearch import Elasticsearch
from fastapi import Form
from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Security,
    File,
    UploadFile,
    Request,
)
from app.models.metadata import (
    MongoDBRef,
    MetadataAgent,
    MetadataIn,
    MetadataDB,
    MetadataOut,
    MetadataPatch,
    validate_context,
    patch_metadata,
    MetadataDelete,
    MetadataDefinitionDB,
)
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from minio import Minio
from pika.adapters.blocking_connection import BlockingChannel
from rocrate.model.person import Person
from rocrate.rocrate import ROCrate

from app import dependencies
from app.config import settings
from app.deps.authorization_deps import Authorization
from app.keycloak_auth import (
    get_token,
    get_user,
    get_current_user,
)
from app.models.authorization import AuthorizationDB, RoleType
from app.models.datasets import (
    DatasetBase,
    DatasetIn,
    DatasetDB,
    DatasetOut,
    DatasetPatch,
    DatasetDBViewList,
    DatasetStatus,
)
from app.models.files import FileOut, FileDB, FileDBViewList
from app.models.folders import FolderOut, FolderIn, FolderDB, FolderDBViewList
from app.models.metadata import MetadataDB
from app.models.pyobjectid import PyObjectId
from app.models.users import UserOut
from app.models.thumbnails import ThumbnailDB
from app.rabbitmq.listeners import submit_dataset_job
from app.routers.files import add_file_entry, remove_file_entry
from app.search.connect import (
    delete_document_by_id,
)
from app.search.index import index_dataset

router = APIRouter()
security = HTTPBearer()

clowder_bucket = os.getenv("MINIO_BUCKET_NAME", "clowder")


async def _get_folder_hierarchy(
    folder_id: str,
    hierarchy: str,
):
    """Generate a string of nested path to folder for use in zip file creation."""
    folder = await FolderDB.get(PydanticObjectId(folder_id))
    hierarchy = folder.name + "/" + hierarchy
    if folder.parent_folder is not None:
        hierarchy = await _get_folder_hierarchy(folder.parent_folder, hierarchy)
    return hierarchy


@router.get("", response_model=List[DatasetOut])
async def get_datasets(
    skip: int = 0,
    limit: int = 10,
):
    query = [DatasetDB.status == DatasetStatus.PUBLIC]
    datasets = await DatasetDB.find(*query).skip(skip).limit(limit).to_list()
    print(str(datasets))
    return [dataset.dict() for dataset in datasets]


@router.get("/{dataset_id}", response_model=DatasetOut)
async def get_dataset(
    dataset_id: str,
):
    if (dataset := await DatasetDB.get(PydanticObjectId(dataset_id))) is not None:
        if dataset.status == DatasetStatus.PUBLIC.name:
            return dataset.dict()
    raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")


@router.get("/{dataset_id}/files", response_model=List[FileOut])
async def get_dataset_files(
    dataset_id: str,
    folder_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
):
    if (dataset := await DatasetDB.get(PydanticObjectId(dataset_id))) is not None:
        if dataset.status == DatasetStatus.PUBLIC.name:
            query = [
                FileDBViewList.dataset_id == ObjectId(dataset_id),
            ]
            if folder_id is not None:
                query.append(FileDBViewList.folder_id == ObjectId(folder_id))
            files = await FileDBViewList.find(*query).skip(skip).limit(limit).to_list()
            return [file.dict() for file in files]
    raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")


@router.get("/{dataset_id}/folders", response_model=List[FolderOut])
async def get_dataset_folders(
    dataset_id: str,
    parent_folder: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
):
    if (dataset := await DatasetDB.get(PydanticObjectId(dataset_id))) is not None:
        if dataset.status == DatasetStatus.PUBLIC.name:
            query = [
                FolderDBViewList.dataset_id == ObjectId(dataset_id),
            ]
            if parent_folder is not None:
                query.append(FolderDBViewList.parent_folder == ObjectId(parent_folder))
            else:
                query.append(FolderDBViewList.parent_folder == None)
            folders = (
                await FolderDBViewList.find(*query).skip(skip).limit(limit).to_list()
            )
            return [folder.dict() for folder in folders]
    raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")


@router.get("/{dataset_id}/metadata", response_model=List[MetadataOut])
async def get_dataset_metadata(
    dataset_id: str,
    listener_name: Optional[str] = Form(None),
    listener_version: Optional[float] = Form(None),
):
    if (dataset := await DatasetDB.get(PydanticObjectId(dataset_id))) is not None:
        if dataset.status == DatasetStatus.PUBLIC.name:
            query = [MetadataDB.resource.resource_id == ObjectId(dataset_id)]

            if listener_name is not None:
                query.append(MetadataDB.agent.listener.name == listener_name)
            if listener_version is not None:
                query.append(MetadataDB.agent.listener.version == listener_version)

            metadata = []
            async for md in MetadataDB.find(*query):
                if md.definition is not None:
                    if (
                        md_def := await MetadataDefinitionDB.find_one(
                            MetadataDefinitionDB.name == md.definition
                        )
                    ) is not None:
                        md.description = md_def.description
                metadata.append(md)
            return [md.dict() for md in metadata]
        else:
            raise HTTPException(
                status_code=404, detail=f"Dataset {dataset_id} not found"
            )
    else:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")


@router.get("/{dataset_id}/download", response_model=DatasetOut)
async def download_dataset(
    dataset_id: str,
    fs: Minio = Depends(dependencies.get_fs),
):
    if (dataset := await DatasetDB.get(PydanticObjectId(dataset_id))) is not None:
        if dataset.status == DatasetStatus.PUBLIC.name:
            current_temp_dir = tempfile.mkdtemp(prefix="rocratedownload")
            crate = ROCrate()

            manifest_path = os.path.join(current_temp_dir, "manifest-md5.txt")
            bagit_path = os.path.join(current_temp_dir, "bagit.txt")
            bag_info_path = os.path.join(current_temp_dir, "bag-info.txt")
            tagmanifest_path = os.path.join(current_temp_dir, "tagmanifest-md5.txt")

            with open(manifest_path, "w") as f:
                pass  # Create empty file so no errors later if the dataset is empty

            with open(bagit_path, "w") as f:
                f.write("Bag-Software-Agent: clowder.ncsa.illinois.edu" + "\n")
                f.write("Bagging-Date: " + str(datetime.datetime.now()) + "\n")

            with open(bag_info_path, "w") as f:
                f.write("BagIt-Version: 0.97" + "\n")
                f.write("Tag-File-Character-Encoding: UTF-8" + "\n")

            # Write dataset metadata if found
            metadata = await MetadataDB.find(
                MetadataDB.resource.resource_id == ObjectId(dataset_id)
            ).to_list()
            if len(metadata) > 0:
                datasetmetadata_path = os.path.join(
                    current_temp_dir, "_dataset_metadata.json"
                )
                metadata_content = json_util.dumps(metadata)
                with open(datasetmetadata_path, "w") as f:
                    f.write(metadata_content)
                crate.add_file(
                    datasetmetadata_path,
                    dest_path="metadata/_dataset_metadata.json",
                    properties={"name": "_dataset_metadata.json"},
                )

            bag_size = 0  # bytes
            file_count = 0

            async for file in FileDB.find(FileDB.dataset_id == ObjectId(dataset_id)):
                file_count += 1
                file_name = file.name
                if file.folder_id is not None:
                    hierarchy = await _get_folder_hierarchy(file.folder_id, "")
                    dest_folder = os.path.join(current_temp_dir, hierarchy.lstrip("/"))
                    if not os.path.isdir(dest_folder):
                        os.mkdir(dest_folder)
                    file_name = hierarchy + file_name
                current_file_path = os.path.join(
                    current_temp_dir, file_name.lstrip("/")
                )

                content = fs.get_object(settings.MINIO_BUCKET_NAME, str(file.id))
                file_md5_hash = hashlib.md5(content.data).hexdigest()
                with open(current_file_path, "wb") as f1:
                    f1.write(content.data)
                with open(manifest_path, "a") as mpf:
                    mpf.write(file_md5_hash + " " + file_name + "\n")
                crate.add_file(
                    current_file_path,
                    dest_path="data/" + file_name,
                    properties={"name": file_name},
                )
                content.close()
                content.release_conn()

                current_file_size = os.path.getsize(current_file_path)
                bag_size += current_file_size

                metadata = await MetadataDB.find(
                    MetadataDB.resource.resource_id == ObjectId(dataset_id)
                ).to_list()
                if len(metadata) > 0:
                    metadata_filename = file_name + "_metadata.json"
                    metadata_filename_temp_path = os.path.join(
                        current_temp_dir, metadata_filename
                    )
                    metadata_content = json_util.dumps(metadata)
                    with open(metadata_filename_temp_path, "w") as f:
                        f.write(metadata_content)
                    crate.add_file(
                        metadata_filename_temp_path,
                        dest_path="metadata/" + metadata_filename,
                        properties={"name": metadata_filename},
                    )

            bag_size_kb = bag_size / 1024

            with open(bagit_path, "a") as f:
                f.write("Bag-Size: " + str(bag_size_kb) + " kB" + "\n")
                f.write("Payload-Oxum: " + str(bag_size) + "." + str(file_count) + "\n")
                f.write("Internal-Sender-Identifier: " + dataset_id + "\n")
                f.write("Internal-Sender-Description: " + dataset.description + "\n")
            crate.add_file(
                bagit_path, dest_path="bagit.txt", properties={"name": "bagit.txt"}
            )
            crate.add_file(
                manifest_path,
                dest_path="manifest-md5.txt",
                properties={"name": "manifest-md5.txt"},
            )
            crate.add_file(
                bag_info_path,
                dest_path="bag-info.txt",
                properties={"name": "bag-info.txt"},
            )

            # Generate tag manifest file
            manifest_md5_hash = hashlib.md5(
                open(manifest_path, "rb").read()
            ).hexdigest()
            bagit_md5_hash = hashlib.md5(open(bagit_path, "rb").read()).hexdigest()
            bag_info_md5_hash = hashlib.md5(
                open(bag_info_path, "rb").read()
            ).hexdigest()

            with open(tagmanifest_path, "w") as f:
                f.write(bagit_md5_hash + " " + "bagit.txt" + "\n")
                f.write(manifest_md5_hash + " " + "manifest-md5.txt" + "\n")
                f.write(bag_info_md5_hash + " " + "bag-info.txt" + "\n")
            crate.add_file(
                tagmanifest_path,
                dest_path="tagmanifest-md5.txt",
                properties={"name": "tagmanifest-md5.txt"},
            )

            zip_name = dataset.name + ".zip"
            path_to_zip = os.path.join(current_temp_dir, zip_name)
            crate.write_zip(path_to_zip)
            f = open(path_to_zip, "rb", buffering=0)
            zip_bytes = f.read()
            stream = io.BytesIO(zip_bytes)
            f.close()
            try:
                shutil.rmtree(current_temp_dir)
            except Exception as e:
                print("could not delete file")
                print(e)

            # Get content type & open file stream
            response = StreamingResponse(
                stream,
                media_type="application/x-zip-compressed",
            )
            response.headers["Content-Disposition"] = (
                "attachment; filename=%s" % zip_name
            )
            # Increment download count
            await dataset.update(Inc({DatasetDB.downloads: 1}))
            return response
        else:
            raise HTTPException(
                status_code=404, detail=f"Dataset {dataset_id} not found"
            )
    raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
