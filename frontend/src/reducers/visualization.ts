import { DataAction } from "../types/action";
import { VisualizationConfigOut, VisualizationOut } from "../openapi/v2";
import { VisualizationState } from "../types/data";
import {
	DOWNLOAD_VIS_DATA,
	GENERATE_VIS_URL,
	GET_VIS_CONFIG,
	GET_VIS_DATA,
	GET_VIS_DATA_PRESIGNED_URL,
} from "../actions/visualization";

const defaultState: VisualizationState = {
	visData: <VisualizationOut>{},
	visConfig: <VisualizationConfigOut[]>[],
	url: "",
	presigned_url: "",
	blob: new Blob([]),
};

const visualization = (state = defaultState, action: DataAction) => {
	switch (action.type) {
		case GET_VIS_DATA:
			return Object.assign({}, state, { visData: action.visData });
		case GET_VIS_CONFIG:
			return Object.assign({}, state, { visConfig: action.visConfig });
		case DOWNLOAD_VIS_DATA:
			return Object.assign({}, state, { blob: action.blob });
		case GENERATE_VIS_URL:
			return Object.assign({}, state, { url: action.url });
		case GET_VIS_DATA_PRESIGNED_URL:
			return Object.assign({}, state, { presigned_url: action.presigned_url });
		default:
			return state;
	}
};

export default visualization;
