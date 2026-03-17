#!/usr/bin/env python3
import PyPDF2
import os
import re
import unicodedata
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
    paravolo_entries = []  # list of tuples (ID, filename, text)
    deltio_id = ID()
    deltio_text = None
    try:
        with os.scandir(directory) as it:
            for entry in it:
                if entry.name.startswith("KPG-Deltio"):
                    deltio_found = True
                    deltio_text = getPDF(entry)
                    deltio_id = read_id_from_deltio(deltio_text)

                if entry.name.startswith("viewParavolo"):
                    paravolo_found = True
                    if check_desmeush(entry):
                        desmeush_found = True
                        text = getPDF(entry)
                        paravolo_entries.append((read_id_from_paravolo(text), entry.name, text))

    except PermissionError as e:
        print(e.strerror, ': \'', e.filename, '\'', sep='')

    if paravolo_found is False:
        print(colored(f"Δεν βρέθηκε παράβολο στον φάκελο {directory}...", "red"))
    elif desmeush_found is False:
        print(colored(
            f"Το παράβολο στον φάκελο {directory} δεν έχει γίνει δέσμευση!!!", "red"))

    if deltio_found is False:
        print(colored(f"Δεν βρέθηκε το δελτίο εξεταζομένου στον φάκελο {directory}...", "cyan"))

    if paravolo_found and deltio_found:
        if not desmeush_found:
            return

        # Ensure every committed paravolo matches the deltio.
        mismatches = [(p, f) for p, f, _ in paravolo_entries if not check_ids(p, deltio_id)]
        if mismatches:
            print(colored(
                f"Δεν ταιριάζουν τα στοιχεία δελτίου-παραβόλου στον φάκελο {directory}...", "yellow"))
            for paravolo_id, filename in mismatches:
                print(f"Παράβολο ({filename}): {paravolo_id}")
            print(f"Δελτίο: {deltio_id}")

        # Check that the deltio level matches a committed viewParavolo file.
        levels = extract_deltio_levels(deltio_text)
        if not levels:
            print(colored(
                f"Το δελτίο {directory} δεν περιέχει κάποιο από τα απαιτούμενα κείμενα επιπέδων (Α, Β, Γ).", "yellow"))
        else:
            level_to_expected = {
                "Επίπεδο Α (Α1 + Α2)": "Για κοινό διαβαθμισμένο test επιπέδων Α1-Α2",
                "Επίπεδο Β (Β1 + Β2)": "Για κοινό διαβαθμισμένο test επιπέδων Β1-Β2",
                "Επίπεδο Γ (Γ1 + Γ2)": "Για κοινό διαβαθμισμένο test επιπέδων Γ1-Γ2",
            }

            for level in sorted(levels):
                expected = level_to_expected.get(level)
                if expected is None:
                    continue
                found = any(re.search(re.escape(expected), text) for _, _, text in paravolo_entries)
                if not found:
                    print(colored(
                        f"Το δελτίο περιέχει '{level}' αλλά δεν βρέθηκε αντίστοιχο αρχείο viewParavolo με '{expected}' στον φάκελο {directory}.",
                        "yellow"))


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


def normalize_name(value: str) -> str:
    """Normalize names extracted from the PDFs.

    - Trim leading/trailing whitespace
    - Replace hyphens with spaces
    - Collapse runs of whitespace to a single space
    - Strip accent marks (Greek and other languages)
    """
    if value is None:
        return value

    # Normalize whitespace/hyphens first so accent stripping doesn't reintroduce extra spaces.
    value = value.strip().replace('-', ' ')
    value = re.sub(r"\s+", " ", value)

    # Strip combining diacritics (accents) from letters.
    normalized = unicodedata.normalize("NFD", value)
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", stripped)


def read_id_from_paravolo(text):
    id = ID()
    match = re.search(r"Όνομα:\s+(.+)", text)
    id.name = normalize_name(match.group(1))
    match = re.search(r"Επώνυμο:\s+(.+)", text)
    id.surname = normalize_name(match.group(1))
    match = re.search(r"Πατρώνυμο:\s+(.+)", text)
    id.fathers_name = normalize_name(match.group(1))
    match = re.search(r"Μητρώνυμο:\s+(.+)", text)
    id.mothers_name = normalize_name(match.group(1))
    return id


def read_id_from_deltio(text):
    id = ID()
    match = re.search(r"ΚΩΔΙΚΟΣ ΥΠΟΨΗΦΙΟΥ\n(.+)\n(.+)\n(.+)\n(.+)", text)
    id.surname = normalize_name(match.group(1))
    id.name = normalize_name(match.group(2))
    id.fathers_name = normalize_name(match.group(3))
    id.mothers_name = normalize_name(match.group(4))
    return id


def extract_deltio_levels(text):
    """Extract the declared level(s) from a KPG-Deltio document.

    The deltio should contain one or more of the following phrases:
      - Επίπεδο Α (Α1 + Α2)
      - Επίπεδο Β (Β1 + Β2)
      - Επίπεδο Γ (Γ1 + Γ2)

    Returns the set of matching phrases found.
    """
    if not text:
        return set()

    patterns = {
        "Επίπεδο Α (Α1 + Α2)": r"Επίπεδο\s*Α\s*\(\s*Α1\s*\+\s*Α2\s*\)",
        "Επίπεδο Β (Β1 + Β2)": r"Επίπεδο\s*Β\s*\(\s*Β1\s*\+\s*Β2\s*\)",
        "Επίπεδο Γ (Γ1 + Γ2)": r"Επίπεδο\s*Γ\s*\(\s*Γ1\s*\+\s*Γ2\s*\)",
    }

    found = set()
    for label, pat in patterns.items():
        if re.search(pat, text):
            found.add(label)
    return found


def surnames_match(s1: str, s2: str) -> bool:
    """Compare Greek surnames, accepting common feminine/male suffix variants.

    The normalized IDs are expected to be uppercase and accent-free, so we can
    compare them directly and only handle a few common gendered suffix changes.
    """

    if s1 is None or s2 is None:
        return False

    if s1 == s2:
        return True

    # Common male->female suffix mappings (assuming uppercase input).
    suffix_pairs = [
        ("ΟΣ", "ΟΥ"),
        ("ΗΣ", "Η"),
        ("ΗΣ", "ΟΥ"),
        ("ΑΣ", "Α"),
        ("ΕΣ", "ΕΑ"),
    ]

    for male, female in suffix_pairs:
        if s1.endswith(male) and s2 == s1[:-len(male)] + female:
            return True
        if s2.endswith(male) and s1 == s2[:-len(male)] + female:
            return True
        if s1.endswith(female) and s2 == s1[:-len(female)] + male:
            return True
        if s2.endswith(female) and s1 == s2[:-len(female)] + male:
            return True

    return False


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
    if not surnames_match(id1.surname, id2.surname):
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
