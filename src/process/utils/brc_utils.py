#!/usr/bin/env python

####################
# Required Modules #
####################

# Libs
import pandas as pd
import pytesseract
import tabula
from pdf2image import convert_from_path
from ...config import poppler_path, tesseract_path

##################
# Configurations #
##################

pytesseract.pytesseract.tesseract_cmd = tesseract_path

#############
# Functions #
#############

def add_column(table, name, val, fill=False):
    """
    Insert column with specified name and value at first row only.

    Args:
        table (pandas.core.frame.DataFrame): Dataframe of table to insert column into
        name (str): Name of column
        val (str): Value of column
        fill (bool): Whether to fill column with value or leave it blank. Defaults to False

    Returns:
        table (pandas.core.frame.DataFrame): Dataframe with new column
    """
    if fill:
        table.insert(0, name, val)
    else:
        table.insert(0, name, '')
        table.at[0, name] = val
    return table


def get_date_req(file_path, page_no):
    """
    Get date required from PDF.

    Args:
        file_path (str): Path to PDF file
        page_no (int): Page number of PDF file

    Returns:
        date_req (str): Date required
    """
    images = convert_from_path(file_path, poppler_path=poppler_path)

    # Convert image to grayscale
    img = images[page_no].convert('L')

    # Perform OCR using pytesseract
    text = pytesseract.image_to_string(img)
    lines = text.split('\n')

    # Get date required
    for l in lines:
        if "DATE REQUIRED" in l.upper():
            loc = l.find('/')
            date_req = l[loc-2:loc+8]
            break
        
    return date_req


def get_table(file_path):
    """
    Get table from PDF.

    Args:
        file_path (str): Path to PDF file

    Returns:
        table (pandas.core.frame.DataFrame): Dataframe of table
    """
    # Initialize variables
    page_no = 1
    found_total = False
    table = pd.DataFrame()
    table_list = tabula.read_pdf(file_path, pages=page_no)

    # Loop through pages to find page with total SGD
    while not found_total:
        if len(table_list) == 2:
            table = pd.concat([table, table_list[0]], ignore_index=True)
            total_idx = 1
            found_total = True
        elif len(table_list[0].columns) != 9:
            total_idx = 0
            found_total = True
        else:
            table = pd.concat([table, table_list[0]], ignore_index=True)
            page_no += 1
            table_list = tabula.read_pdf(file_path, pages=page_no)

    # Drop unwanted columns
    drop = ['IT', 'UNIT', 'UNIT PRICE', 'PER', 'DISC.']
    table.drop(drop, axis=1, inplace=True)

    # Get date required
    page_req = get_date_req(file_path, page_no)
    table = add_column(table, 'DATE REQ.', page_req, fill=True)

    # Get total amount in SGD
    [total] = [table_list[total_idx].columns[i+1] for i in range(len(table_list[total_idx].columns)) if 'SGD' in table_list[total_idx].columns[i]]
    table = add_column(table, 'TOTAL AMT', total, fill=False)

    # Replace values
    table.replace(to_replace=r'\r', value=' ', regex=True, inplace=True)
    table.replace(to_replace=',', value='', regex=True, inplace=True)

    # Rename columns
    table.rename(columns={'$ AMOUNT': 'PDF SUBTOTAL'}, inplace=True)

    # Fill in blank values in DO/NO and convert to integer
    table['DO/NO'] = table['DO/NO'].ffill()
    table['DO/NO'] = table['DO/NO'].astype(int)

    # Convert QTY to 6 d.p.
    table.loc[table['QTY'] != '', 'QTY'] = pd.to_numeric(table.loc[table['QTY'] != '', 'QTY'], errors='coerce').round(6)

    return table


def complete_table(table, lines):
    """
    Complete table with all other required variables.

    Args:
        table (pandas.core.frame.DataFrame): Dataframe of table
        lines (list): List of lines from PDF

    Returns:
        table (pandas.core.frame.DataFrame): Dataframe of table with all other required variables
    """
    for i in range(len(lines)):
        # Get Invoice no.
        if 'INVOICE NO' in lines[i].upper():
            inv_no = lines[i].split(':')[-1].strip()
            table = add_column(table, 'INVOICE NO. 1', inv_no, fill=False)
            table = add_column(table, 'INVOICE NO. 2', inv_no, fill=True)

        # Get Invoice date
        if ('DATE' in lines[i].upper()) and ('DUE' not in lines[i].upper()):
            inv_date = lines[i].split(':')[-1].strip()
            table = add_column(table, 'INVOICE DATE', inv_date, fill=False)

        # Get Order ref. no.
        if 'CUSTOMER ORDER REF' in lines[i].upper():
            order_ref = lines[i].split(':')[1].strip().split(' ')[0].strip()
            table = add_column(table, 'ORDER REF.', order_ref, fill=True)

            if order_ref.upper() == 'SAMPLE':
                # Get location
                location = 'SAMPLE'
                
                # Get subcon
                start = lines[i+1].find('(') + 1
                end = lines[i+1].find(')')
                subcon = lines[i+1][start:end]

            else:
                # Get location
                location = order_ref.split('/')[-1]

                # Get subcon
                subcon = order_ref.split('/')[1]
                
            table = add_column(table, 'LOCATION', location, fill=True)
            table = add_column(table, 'SUBCON', subcon, fill=True)

    # Get MMMM YY
    mmmm_yy = pd.to_datetime(inv_date).strftime('%Y %m')
    table = add_column(table, 'FOR MONTH (YYYY MM)', mmmm_yy, fill=True)

    # Insert blank columns
    table.insert(0, 'ZONE', '')
    table.insert(0, 'CODE 1', '')
    table.insert(0, 'CODE 2', '')  

    return table
