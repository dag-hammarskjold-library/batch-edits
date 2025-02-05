# https://ask.un.org/admin/ticket?qid=14959124
# delete the 856 values specified in data.txt

import sys
from dlx import DB
from dlx.marc import Bib

DB.connect(sys.argv[1], database=sys.argv[2])

for line in open(sys.argv[3]).readlines()[1:]:
    line = line.strip()
    rid, link = line.split('\t')
    bib = Bib.from_id(int(rid))

    # get the field with the deal link
    if field := next(filter(lambda x: link == x.get_value('u'), bib.get_fields('856')), None):
        print(f'Deleting field and saving bib# {rid}')
        bib.delete_field(field)
        bib.commit(user='admin')
