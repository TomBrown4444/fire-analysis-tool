# Data Directory

This directory is used to store cached data from the FIRMS API and other temporary files.

## Structure

- `cache/`: Contains cached API responses to reduce redundant API calls
- `exports/`: Stores exported timeline GIFs and other visualization outputs
- `temp/`: Temporary files used during processing

## Note

Data in this directory is not committed to version control as per the `.gitignore` settings. 
Each user will generate their own local cache when running the application.