import os


def get_template_file_list():
    file_list = os.listdir(__file__)
    if "test.py" in file_list:
        file_list.remove("test.py")

    return file_list



TEMPLATE_FILES = get_template_file_list()


TEMPLATE_INSTRUCTIONS = {

}




