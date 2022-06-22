import {
	RECEIVE_FILES_IN_DATASET,
	RECEIVE_DATASET_ABOUT,
	UPDATE_DATASET,
	RECEIVE_DATASETS,
	DELETE_DATASET,
	CREATE_DATASET,
	RESET_CREATE_DATASET,
	FOLDER_ADDED, RECEIVE_FOLDERS_IN_DATASET, GET_FOLDER_PATH,
	DOWNLOAD_DATASET
} from "../actions/dataset";
import {CREATE_FILE, UPDATE_FILE, DELETE_FILE, RESET_CREATE_FILE} from "../actions/file";
import {DataAction} from "../types/action";
import {Author, Dataset, File, DatasetState} from "../types/data";

const defaultState: DatasetState = {
	files: [],
	about: <Dataset>{"author":<Author>{}},
	datasets: [],
	newDataset: <Dataset>{},
	newFile: <File>{},
	folders: [],
	folderPath: []
};

const dataset = (state = defaultState, action: DataAction) => {
	switch (action.type) {
	case RECEIVE_FILES_IN_DATASET:
		return Object.assign({}, state, {files: action.files});
	case RECEIVE_FOLDERS_IN_DATASET:
		return Object.assign({}, state, {folders: action.folders});
	case DELETE_FILE:
		return Object.assign({}, state, {
			files: state.files.filter(file => file.id !== action.file.id),
		});
	// TODO rethink the pattern for file creation
	// case CREATE_FILE:
	// 	return Object.assign({}, state, {
	// 		files: [...state.files, action.file]
	// 	});
	case CREATE_FILE:
		return Object.assign({}, state, {
			newFile: action.file
		});
	case RESET_CREATE_FILE:
		return Object.assign({}, state, {newFile: {}})
	case UPDATE_FILE:
		return Object.assign({}, state, {
			files: state.files.map(file => file.id === action.file.id ? action.file: file),
		});
	case RECEIVE_DATASET_ABOUT:
		return Object.assign({}, state, {about: action.about});
	case UPDATE_DATASET:
		return Object.assign({}, state, {about: action.about});
	case RECEIVE_DATASETS:
		return Object.assign({}, state, {datasets: action.datasets});
	case CREATE_DATASET:
		return Object.assign({}, state, {newDataset: action.dataset});
	case RESET_CREATE_DATASET:
			return Object.assign({}, state, {newDataset: {}});
	case DELETE_DATASET:
		return Object.assign({}, state, {
			datasets: state.datasets.filter(dataset => dataset.id !== action.dataset.id),
		});
	case FOLDER_ADDED:
		return Object.assign({}, state, {
			folders: [...state.folders, action.folder]
		});
	case GET_FOLDER_PATH:
		return Object.assign({}, state, {
			folderPath: action.folderPath
		});
	case DOWNLOAD_DATASET:
		// TODO do nothing for now; but in the future can utilize to display certain effects
		return Object.assign({}, state, {});
	default:
		return state;
	}
};

export default dataset;
