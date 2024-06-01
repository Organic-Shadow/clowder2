import React, { useState } from "react";
import {
	Container,
	Dialog,
	DialogTitle,
	DialogContent,
	DialogActions,
	Button,
	TextField,
	Box,
} from "@mui/material";
import licenseSchema from "../../schema/licenseSchema.json";
import { FormProps } from "@rjsf/core";
import { ClowderRjsfErrorList } from "../styledComponents/ClowderRjsfErrorList";
import Form from "@rjsf/material-ui";
import { useDispatch, useSelector } from "react-redux";
import { ClowderRjsfTextWidget } from "../styledComponents/ClowderRjsfTextWidget";
import { ClowderRjsfTextAreaWidget } from "../styledComponents/ClowderRjsfTextAreaWidget";
import { ClowderRjsfSelectWidget } from "../styledComponents/ClowderRjsfSelectWidget";
import { RootState } from "../../types/data";
import { updateDatasetLicense } from "../../actions/dataset"; // Import LicenseOut type

type EditLicenseModalProps = {
	setEditLicenseOpen: any;
};

export const EditLicenseModal = (props: EditLicenseModalProps) => {
	const { setEditLicenseOpen } = props;

	const dispatch = useDispatch();

	const editLicense = (formData: FormData) =>
		dispatch(updateDatasetLicense(license.id, formData));

	const license = useSelector((state: RootState) => state.dataset.license);

	const onSave = async () => {
		// Handle save operation here
	};

	return (
		<Container>
			<Form
				schema={licenseSchema["schema"] as FormProps<any>["schema"]}
				//uiSchema={licenseSchema["uiSchema"] as FormProps<any>["uiSchema"]}
				formData={license}
				onSubmit={({ formData }) => {
					editLicense(formData);
					// close modal
					setEditLicenseOpen(false);
				}}
				ErrorList={ClowderRjsfErrorList}
			>
				<Box className="inputGroup" sx={{ float: "right" }}>
					<Button variant="contained" type="submit">
						Update
					</Button>
					<Button
						onClick={() => {
							setEditLicenseOpen(false);
						}}
						sx={{ marginLeft: "0.5em" }}
					>
						Cancel
					</Button>
				</Box>
			</Form>
		</Container>
	);
};
