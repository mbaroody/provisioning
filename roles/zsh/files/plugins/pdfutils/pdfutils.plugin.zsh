#!/usr/bin/env zsh

pdf_replace_range_with() {
    # Check for correct number of arguments
    if [ "$#" -ne 3 ]; then
        echo "Usage: $0 <input_pdf> <range> <replacement_pdf>"
        echo "Example: $0 mypdf1.pdf 455-644 replacement.pdf"
        exit 1
    fi

    # Parse arguments
    input_pdf="$1"
    range="$2"
    replacement_pdf="$3"

    # Validate the range format
    if [[ ! "$range" =~ ^[0-9]+-[0-9]+$ ]]; then
        echo "Error: Range must be in the format 'start-end' (e.g., 455-644)"
        exit 1
    fi

    # Extract start and end pages from the range
    start_page=$(echo "$range" | cut -d'-' -f1)
    end_page=$(echo "$range" | cut -d'-' -f2)

    # Check if start and end are positive numbers
    if ! [[ "$start_page" =~ ^[1-9][0-9]*$ ]] || ! [[ "$end_page" =~ ^[1-9][0-9]*$ ]]; then
        echo "Error: Start and end pages must be positive integers."
        exit 1
    fi

    # Check if start_page is less than end_page
    if [ "$start_page" -ge "$end_page" ]; then
        echo "Error: Start page must be less than end page."
        exit 1
    fi

    # Get the total number of pages in the input PDF using pdftk
    total_pages=$(pdftk "$input_pdf" dump_data | grep NumberOfPages | awk '{print $2}')

    # Check if range is within bounds
    if [ "$start_page" -lt 1 ] || [ "$end_page" -gt "$total_pages" ]; then
        echo "Error: Range $range is out of bounds. The PDF has $total_pages pages."
        exit 1
    fi

    # Define output file name
    output_pdf="output.pdf"

    # Check for the edge case where the range is the entire PDF
    if [ "$start_page" -eq 1 ] && [ "$end_page" -eq "$total_pages" ]; then
        echo "The range covers the entire PDF. Replacing the entire content with the replacement PDF."
        cp "$replacement_pdf" "$output_pdf"
    else
        # Define temporary file names for split parts
        part1="part1.pdf"
        part3="part3.pdf"

        # Check the special cases for start of range and end of range
        if [ "$start_page" -eq 1 ]; then
            echo "Range starts at the first page."
            # No need to extract part1, just use the replacement PDF and part3
            pdftk "$input_pdf" cat $(($end_page + 1))-end output "$part3"
            pdftk "$replacement_pdf" "$part3" cat output "$output_pdf"
            rm -f "$part3"
        elif [ "$end_page" -eq "$total_pages" ]; then
            echo "Range ends at the last page."
            # No need to extract part3, just use part1 and the replacement PDF
            pdftk "$input_pdf" cat 1-$(($start_page - 1)) output "$part1"
            pdftk "$part1" "$replacement_pdf" cat output "$output_pdf"
            rm -f "$part1"
        else
            # Default case: split into three parts
            pdftk "$input_pdf" cat 1-$(($start_page - 1)) output "$part1"
            pdftk "$input_pdf" cat $(($end_page + 1))-end output "$part3"
            pdftk "$part1" "$replacement_pdf" "$part3" cat output "$output_pdf"
            rm -f "$part1" "$part3"
        fi
    fi

    echo "The output PDF has been created as $output_pdf"
}

pdf_insert_before_page() {
    # Check if pdftk is installed
    if ! command -v pdftk &> /dev/null; then
        echo "Error: pdftk is not installed. Please install it to use this script."
        exit 1
    fi

    # Check for correct number of arguments
    if [ "$#" -ne 3 ]; then
        echo "Usage: $0 <input_pdf> <start_page> <insert_pdf>"
        echo "Example: $0 mypdf1.pdf 5 insert.pdf"
        exit 1
    fi

    # Parse arguments
    input_pdf="$1"
    start_page="$2"
    insert_pdf="$3"

    # Validate that the input PDF exists
    if [ ! -f "$input_pdf" ]; then
        echo "Error: Input PDF '$input_pdf' does not exist."
        exit 1
    fi

    # Validate that the insert PDF exists
    if [ ! -f "$insert_pdf" ]; then
        echo "Error: Insert PDF '$insert_pdf' does not exist."
        exit 1
    fi

    # Validate that start_page is a positive integer
    if ! [[ "$start_page" =~ ^[1-9][0-9]*$ ]]; then
        echo "Error: Start page must be a positive integer."
        exit 1
    fi

    # Get the total number of pages in the input PDF using pdftk
    total_pages=$(pdftk "$input_pdf" dump_data | grep NumberOfPages | awk '{print $2}')

    # Check if start_page is within bounds
    if [ "$start_page" -lt 1 ] || [ "$start_page" -gt "$total_pages" ]; then
        echo "Error: Start page $start_page is out of bounds. The PDF has $total_pages pages."
        exit 1
    fi

    # Define output file name
    output_pdf="output.pdf"

    # Define temporary file names for split parts
    part1="part1.pdf"
    part2="part2.pdf"

    # Split the input PDF into two parts
    if [ "$start_page" -eq 1 ]; then
        echo "Inserting at the very beginning of the PDF."
        # No part1 needed; insert at the start
        pdftk "$input_pdf" cat "$start_page"-end output "$part2"
        pdftk "$insert_pdf" "$part2" cat output "$output_pdf"
        rm -f "$part2"
    elif [ "$start_page" -eq "$total_pages" ]; then
        echo "Inserting just before the last page."
        # No part2 needed; insert at the end
        pdftk "$input_pdf" cat 1-$(($start_page - 1)) output "$part1"
        pdftk "$part1" "$insert_pdf" cat output "$output_pdf"
        rm -f "$part1"
    else
        # General case: split into part1 and part2
        pdftk "$input_pdf" cat 1-$(($start_page - 1)) output "$part1"
        pdftk "$input_pdf" cat "$start_page"-end output "$part2"
        pdftk "$part1" "$insert_pdf" "$part2" cat output "$output_pdf"
        rm -f "$part1" "$part2"
    fi

    echo "The output PDF has been created as $output_pdf"
}
