
import os
root_folder = os.path.dirname(os.path.abspath(__file__))

def get_resource_path(resource_name: str = '') -> str:
    """ Returns the path to the resource with the given name. """
    return f'{root_folder}/resources/{resource_name}'