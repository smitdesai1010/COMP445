'''
    Status Code: 
        1) 200: All Good
        2) 404: File Not Found
        3) 400: Security issue
        4) 500: Internal Server Error (Maybe failed to open file)

    Return Type: dict
    {
        'statusCode': 'value',
        'data': 'Actual data or the error message'
    }
'''
import os
import shutil
from pathlib import Path

class FileHandler:

    def __init__(self):
        self.defaultDirectory = 'Data'

    def setDefaultDirectory(self, dirName):
        self.defaultDirectory = dirName        
        absolutePath = os.path.join(os.getcwd(), dirName)

        if Path(absolutePath).exists() and Path(absolutePath).is_dir():
            shutil.rmtree(absolutePath)

        Path(absolutePath).mkdir(parents=True)

    '''
        Possbile status code returned: 200
    '''
    def getNamesOfAllFiles(self):
        absolutePath = os.path.join(os.getcwd(), self.defaultDirectory)
        try:
            # Array of file names
            files = [f for f in os.listdir(absolutePath) if os.path.isfile(os.path.join(absolutePath, f))]
            return {
                'statusCode': 200,
                'data': '\n'.join(files)
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'data': f'Error getting names of files: {e}'
            }

    '''
        Possbile status code returned: 200, 400, 404
    '''
    def getFileContent(self,filename):
        filename = self.defaultDirectory + '/' + filename
        try:
            if not Path(filename).exists() or not Path(filename).is_file():
                return {
                    'statusCode': 404,
                    'data': 'File does not exist.'
                }
                
            with open(filename) as f: 
                file_data = f.read()
            return {
                'data': file_data,
                'statusCode': 200
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'data': f'Error getting file content: {e}'
            }

    '''
        Possbile status code returned: 200, 400, 500
    '''
    def writeToFile(self, filename, filecontent):
        filename = self.defaultDirectory + '/' + filename
        try:
            f = open(filename, "w")
            f.write(filecontent)
            f.close()
            return {
                'data': 'Successfully wrote file content.',
                'statusCode': 200
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'data': f'Error getting file content: {e}'
            }