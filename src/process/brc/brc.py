#!/usr/bin/env python

####################
# Required Modules #
####################

# Libs
import pandas as pd
import streamlit as st
from PyPDF2 import PdfReader

# Custom
from .brc_utils import complete_table, get_table

#############
# Functions #
#############


def brc_main(pdf_file_paths):
    """
    Main function for BRC.

    Args:
        pdf_file_paths (list): List of PDF file paths

    Returns:
        dfs (pandas.core.frame.DataFrame): Dataframe with extracted data
        error_files (list): List of error files
    """
    # Initialize dataframe
    headers = [
        "INVOICE NO. 1",
        "INVOICE DATE",
        "TOTAL AMT",
        "INVOICE NO. 2",
        "FOR MONTH (YYYY MM)",
        "ZONE",
        "LOCATION",
        "SUBCON",
        "ORDER REF.",
        "DATE REQ.",
        "DO/NO",
        "DESCRIPTION",
        "CODE 1",
        "CODE 2",
        "QTY",
        "UNIT",
        "VENDOR INVOICE UNIT PRICE (S$)",
        "PER",
        "PDF SUBTOTAL",
    ]
    dfs = pd.DataFrame(columns=headers)

    # List to hold error files
    error_files = []

    # Create a Streamlit progress bar
    progress = st.progress(0)
    status_text = st.empty()

    # Iterate through files
    for index, f in enumerate(pdf_file_paths):
        try:
            # Get table from PDF
            table = get_table(f)

            # Get other variables of interest
            pdf_file = PdfReader(open(f, "rb"))
            page = pdf_file.pages[0]
            text = page.extract_text()
            lines = text.split("\n")
            
            # Add extracted info to table
            table = complete_table(table, lines)

            # Sort table columns
            table = table[headers]

            # Append to dataframe
            dfs = pd.concat([dfs, table], ignore_index=True)

        except Exception as e:
            # If there's an error, log the file path
            st.error(f"Error processing file {f}: {str(e)}")
            error_files.append(f)

        finally:
            # Update the Streamlit progress bar and status text
            percent_complete = (index + 1) / len(pdf_file_paths)
            progress.progress(percent_complete)
            status_text.text(
                f"Processed: {index + 1}/{len(pdf_file_paths)} files "
                f"({int(percent_complete*100)}% complete)"
            )

    return dfs, error_files
