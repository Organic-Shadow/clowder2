import React, { useEffect } from "react";
import { Box, Typography } from "@mui/material";
import { metadataConfig } from "../../metadata.config";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../types/data";
import { fetchMetadataDefinitions } from "../../actions/metadata";
import metadata from "../../reducers/metadata";

type MetadataType = {
	setMetadata: any;
};

/*
This is the interface when create new dataset and new files
Uses only registered metadata definition to populate the form
 */
export const CreateMetadata = (props: MetadataType) => {
	const { setMetadata, sourceItem } = props;
	console.log("We are creating metadata here");
	const dispatch = useDispatch();
	const getMetadatDefinitions = (
		name: string | null,
		skip: number,
		limit: number
	) => dispatch(fetchMetadataDefinitions(name, skip, limit));
	const metadataDefinitionList = useSelector(
		(state: RootState) => state.metadata.metadataDefinitionList.data
	);
	const datasetRole = useSelector(
		(state: RootState) => state.dataset.datasetRole
	);

	useEffect(() => {
		getMetadatDefinitions(null, 0, 100);
	}, []);

	const checkIfRequiredFieldsAreFilled = () => {
		const requiredFilled = false;
		const fieldValues: Array<boolean> = [];
		metadataDefinitionList.forEach((metadata) => {
			if (metadata.required_for_items.files && sourceItem === "files") {
				metadata.map((field, idxx) => {
					console.log("field", field);
				});
			} else if (
				metadata.required_for_items.datasets &&
				sourceItem === "datasets"
			) {
				metadata.map((field, idxx) => {
					console.log("field", field);
				});
			}
		});
	};

	return (
		<>
			{metadataDefinitionList
				.filter((metadata) => {
					// Add your condition here to filter the metadataDefinitionList
					// For example, you may want to filter based on the sourceItem
					return (
						(sourceItem === "datasets" &&
							metadata.required_for_items.datasets) ||
						(sourceItem === "files" && metadata.required_for_items.files)
					);
				})
				.map((metadata, idx) => {
					return (
						<Box className="inputGroup" key={idx}>
							<Typography variant="h6">
								{metadata.name}
								<span>*</span>
							</Typography>
							<Typography variant="subtitle2">
								{metadata.description}
							</Typography>
							{metadata.fields.map((field, idxx) => {
								console.log(
									"field stuff",
									field.required,
									field,
									field.config.options
								);
								return React.cloneElement(
									// if nothing match fall back to default widget
									metadataConfig[field.widgetType ?? "NA"] ??
										metadataConfig["NA"],
									{
										widgetName: metadata.name,
										fieldName: field.name,
										options: field.config.options ?? [],
										setMetadata: setMetadata,
										initialReadOnly: false,
										initialInputBlank: true,
										isRequired: field.required,
										datasetRole: datasetRole,
										key: idxx,
									}
								);
							})}
						</Box>
					);
				})}
		</>
	);
};
