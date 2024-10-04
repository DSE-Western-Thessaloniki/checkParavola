#!/usr/bin/env python3
import PyPDF2
import os
import re
from optparse import OptionParser
from termcolor import colored


class ID:
    name: str
    surname: str
    fathers_name: str
    mothers_name: str

    def __repr__(self):
        return f"name: {self.name}, surname: {self.surname}, father's name: {self.fathers_name}, mother's name: {self.mothers_name}"


def getPDF(filename):
    # creating a pdf file object
    pdfFileObj = open(filename, 'rb')

    # creating a pdf reader object
    pdfReader = PyPDF2.PdfReader(pdfFileObj)

    # printing number of pages in pdf file
    # print(pdfReader.pages)

    # creating a page object
    pageObj = pdfReader.pages[0]

    # extracting text from page
    text = pageObj.extract_text()

    # closing the pdf file object
    pdfFileObj.close()

    return text


def check_desmeush(file_entry: os.DirEntry[str]):
    if getPDF(file_entry).find("ΔΕΣΜΕΥΜΕΝΟ") != -1:
        return True
    return False


def check_folder(directory):
    paravolo_found = False
    deltio_found = False
    desmeush_found = False
    paravolo_id = ID()
    deltio_id = ID()
    try:
        with os.scandir(directory) as it:
            for entry in it:
                if (entry.name.startswith("KPG-Deltio")):
                    deltio_found = True
                    deltio_id = read_id_from_deltio(getPDF(entry))
                if (entry.name.startswith("viewParavolo")):
                    paravolo_found = True
                    if check_desmeush(entry):
                        desmeush_found = True
                        paravolo_id = read_id_from_paravolo(getPDF(entry))
    except PermissionError as e:
        print(e.strerror, ': \'', e.filename, '\'', sep='')

    if paravolo_found is False:
        print(colored(f"Δεν βρέθηκε παράβολο στον φάκελο {directory}...", "red"))
    elif desmeush_found is False:
        print(colored(
            f"Το παράβολο στον φάκελο {directory} δεν έχει γίνει δέσμευση!!!", "red"))
    if deltio_found is False:
        print(colored(f"Δεν βρέθηκε το δελτίο εξεταζομένου στον φάκελο {directory}...", "cyan"))

    if paravolo_found and deltio_found and not check_ids(paravolo_id, deltio_id):
        print(colored(
            f"Δεν ταιριάζουν τα στοιχεία δελτίου-παραβόλου στον φάκελο {directory}...", "yellow"))
        print(f"Παράβολο: {paravolo_id}")
        print(f"Δελτίο: {deltio_id}")


def check_root(directory):
    try:
        with os.scandir(directory) as it:
            for entry in it:
                if entry.is_dir():
                    check_folder(f'{directory}/{entry.name}')
                else:
                    pass

    except PermissionError as e:
        print(e.strerror, ': \'', e.filename, '\'', sep='')


def read_id_from_paravolo(text):
    id = ID()
    match = re.search(r"Όνομα:\s+(.+)", text)
    id.name = match.group(1)
    match = re.search(r"Επώνυμο:\s+(.+)", text)
    id.surname = match.group(1)
    match = re.search(r"Πατρώνυμο:\s+(.+)", text)
    id.fathers_name = match.group(1)
    match = re.search(r"Μητρώνυμο:\s+(.+)", text)
    id.mothers_name = match.group(1)
    return id


def read_id_from_deltio(text):
    id = ID()
    match = re.search(r"ΚΩΔΙΚΟΣ ΥΠΟΨΗΦΙΟΥ\n(.+)\n(.+)\n(.+)\n(.+)", text)
    id.surname = match.group(1)
    id.name = match.group(2)
    id.fathers_name = match.group(3)
    id.mothers_name = match.group(4)
    return id


def check_ids(id1, id2):
    equal = True

    # Πρώτα έλεγχος αν είναι απόλυτα ίδια τα στοιχεία
    if id1.name != id2.name:
        equal = False
    if id1.surname != id2.surname:
        equal = False
    if id1.fathers_name != id2.fathers_name:
        equal = False
    # if id1.mothers_name != id2.mothers_name:
    #     equal = False

    check1 = equal

    # Έλεγχος αν κατέθεσε ο πατέρας το παράβολο
    equal = True
    if id1.surname != id2.surname:
        equal = False
    if id1.name != id2.fathers_name:
        equal = False

    check2 = equal

    # Έλεγχος αν κατέθεσε η μητέρα το παράβολο
    equal = True
    if id1.name != id2.mothers_name:
        equal = False

    check3 = equal

    return check1 or check2 or check3


def main():
    parser = OptionParser()
    parser.add_option('-d', '--directory', dest='dirname',
                      help='directory to parse', metavar='DIRECTORY')
    (options, args) = parser.parse_args()
    if options.dirname is None:
        parser.print_help()
        exit()
    # print('Dirname:', options.dirname)
    # print('Verbose:', options.verbose)

    # Strip trailing slash
    dir_string = options.dirname
    if dir_string[len(dir_string)-1] == '/':
        dir_string = dir_string[:len(dir_string)-1]

    check_root(dir_string)

    # text = getPDF('viewParavolo.pdf')
    # paravolo_id = read_id_from_paravolo(text)
    # print(paravolo_id)
    # # print(text)

    # text = getPDF('KPG-Deltio_23101076.pdf')
    # # print(text)
    # id = read_id_from_deltio(text)
    # print(id)

    # print(check_ids(paravolo_id, id))


if __name__ == "__main__":
    main()
