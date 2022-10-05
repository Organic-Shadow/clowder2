import React, {useState} from "react";
import {LocalizationProvider, DateTimePicker} from "@mui/lab";
import DateAdapter from "@mui/lab/AdapterDateFns";
import {ClowderMetadataTextField} from "../../styledComponents/ClowderMetadataTextField";
import {MetadataEditButton} from "./MetadataEditButton";
import {Grid} from "@mui/material";


export const MetadataDateTimePicker = (props) => {
	const {widgetName, fieldName, metadataId, contents, setMetadata, initialReadOnly, resourceId, updateMetadata} = props;
	const [localContent, setLocalContent] = useState(contents && contents[fieldName] ? contents: {});

	const [readOnly, setReadOnly] = useState(initialReadOnly);

	const [inputChanged, setInputChanged] = useState(false);

	const handleChange = (newValue:Date) => {
		setInputChanged(true);

		let tempContents: { [key: string]: Date; } = {};
		tempContents[fieldName] = newValue;
		setMetadata ?
			metadataId ?
				setMetadata({
					"id": metadataId,
					"definition": widgetName,
					"contents": tempContents
				})
				:
				setMetadata({
					"definition": widgetName,
					"contents": tempContents
				})
			:
			null
		setLocalContent(tempContents)
	};

	return (
		<div style={{margin:"1.1em auto"}}>
			<Grid container spacing={2} sx={{ "alignItems": "center"}}>
				<Grid item xs={11} sm={11} md={11} lg={11} xl={11}>
					<LocalizationProvider dateAdapter={DateAdapter}>
						<DateTimePicker
							label={widgetName}
							value={readOnly && contents ? contents[fieldName]: localContent[fieldName]}
							onChange={handleChange}
							renderInput={(params) =>
								<ClowderMetadataTextField {...params} fullWidth
														  helperText={inputChanged? "* You have changed this field. " +
															  "Remember to save/ update.": ""}/>}
							disabled={readOnly}
						/>
					</LocalizationProvider>
				</Grid>
				<Grid item xs={1} sm={1} md={1} lg={1} xl={1}>
					<MetadataEditButton readOnly={readOnly} setReadOnly={setReadOnly} updateMetadata={updateMetadata}
										contents={localContent} metadataId={metadataId} resourceId={resourceId}
										widgetName={widgetName} setInputChanged={setInputChanged}
										setMetadata={setMetadata}/>
				</Grid>
			</Grid>
		</div>
	);
}