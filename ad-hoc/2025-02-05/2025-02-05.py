# https://ask.un.org/admin/ticket?qid=14959124
# delete the 856 values specified in data.txt

import sys, os, re
from dlx import DB
from dlx.marc import Bib

DB.connect(sys.argv[1], database=sys.argv[2])

for line in open(sys.argv[3]).readlines()[1:]:
    rid, link = line.split('\t')
    #print([rid, link])
    bib = Bib.from_id(int(rid))
    to_delete = next(filter(lambda x: link == x.get_value('u'), bib.get_fields('856')), None)
    print(to_delete)