"""Run a series of specified edits on a set of DLX records"""

import sys, os, re, json, inspect
from argparse import ArgumentParser
from batch_edits.module import Class # rename package, module and class
from dlx import DB
from dlx.marc import BibSet

def get_args():
    parser = ArgumentParser()
    parser.add_argument('--connect', help='DLX connection string')
    parser.add_argument('--database', help='The database name')

    return parser.parse_args()

def run(**kwargs):
    if kwargs:
        sys.argv = [sys.argv[0]]
        
        for param, arg in kwargs.items():
            sys.argv.append(f'--{param}={arg}')

    if DB.database_name != 'testing':
        args = get_args()
        DB.connect(args.connect)

    bibs = BibSet.from_query({}, sort=[('_id', 1)], limit=1000)
    edits = [f for name, f in inspect.getmembers(sys.modules[__name__], inspect.isfunction) if name[:5] == 'edit_']

    for bib in bibs:
        [bib := edit(bib) for edit in edits]
        bib.commit(user='batch edit 1')

###

def edit_1(bib):
    # 1. BIBLIOGRAPHIC - Delete field 099 - IF subfield c is empty OR if subfield c = internet
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for field in bib.get_fields('099'):
            if field.get_value('c') == 'internet':
                bib.delete_field(field)

    return bib
    
def edit_2(bib):
    # 2. BIBLIOGRAPHIC - Delete field 029 - IF subfield a IS NOT JN or UN
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for field in bib.get_fields('029'):
            if field.get_subfield('a') not in ('JN', 'UN'):
                bib.delete_field(field)
    return bib

def edit_3(bib):
    # 3. BIBLIOGRAPHIC, SPEECHES, VOTING - Delete field 930 - If NOT 930:UND* OR 930:UNGREY* OR 930:CIF* OR 930:DIG* OR 930:HUR*  oR 930:PER*
    for i, field in enumerate(bib.get_fields('930')):
        if not any([re.match(f'^{x}', field.get_value('a')) for x in ('UND', 'UNGREY', 'CIF', 'DIG', 'HUR', 'PER')]):
            bib.delete_field(field.tag, i)

    return bib
        
def edit_4(bib):
    # 4. BIBLIOGRAPHIC, SPEECHES, VOTING - Delete field 000 - No condition
    bib.delete_field('000')
    return bib

def edit_5(bib):
    # 5. BIBLIOGRAPHIC - Delete field 008 - No condition
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        bib.delete_field('008')

    return bib

def edit_6(bib):
    # 6. BIBLIOGRAPHIC, VOTING - Delete field 035 - IF 089__b is NOT B22 (keep 035 for speeches)
    if not any([x == 'Speeches' for x in bib.get_values('989', 'a')]):
        bib.delete_fields('035')

    return bib

def edit_7(bib):
    # 7. BIBLIOGRAPHIC - Delete field 069 - No condition
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        bib.delete_field('069')

    return bib

def edit_8(bib):
    # 8. BIBLIOGRAPHIC - Transfer field 100 - to 700
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for field in bib.get_fields('100'):
            field.tag = '700'

    return bib

def edit_9(bib):
    # 9. BIBLIOGRAPHIC - Transfer field 110 - to 710
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for field in bib.get_fields('110'):
            field.tag = '710'

    return bib

def edit_10(bib):
    # 10. BIBLIOGRAPHIC - Transfer field 111 - to 711
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for field in bib.get_fields('111'):
            field.tag = '711'

    return bib

def edit_11(bib):
    # 11. BIBLIOGRAPHIC - Transfer field 130 - to 730
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for field in bib.get_fields('130'):
            field.tag = '730'

    return bib

def edit_12(bib):
    # 12. BIBLIOGRAPHIC - Delete field 222 - No condition
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        bib.delete_field('222')

    return bib

def edit_13(bib):
    # 13. VOTING, SPEECHES - Delete field 269 - If (089:B22 OR  089:B23) - Only speeches and votes
    if any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        bib.delete_field('269')

    return bib

def edit_14(bib):
    # 14. BIBLIOGRAPHIC - Transfer field 440 - To 830
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for field in bib.get_fields('440'):
            field.tag = '830'

    return bib

def edit_15(bib):
    # 15. BIBLIOGRAPHIC - Transfer field 490 $x - Transfer to 022 $a if the field with the same value does not exists
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for field in bib.get_fields('490'):
            val = field.get_value('x')

            if val not in bib.get_values('022', 'a'):
                bib.set('022', 'a', val, address='+')
                bib.delete_field(field)

    return bib

def edit_16(bib):
    # 16. BIBLIOGRAPHIC - Delete field 597 - If 597:"Retrospective indexing"
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for field in bib.get_fields('597'):
            if field.get_value('a').lower()[:22] == 'retrospective indexing':
                bib.delete_field(field)

    return bib

def edit_17(bib):
    # 17. BIBLIOGRAPHIC - Delete field 773 - No condition
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        bib.delete_field('773')

    return bib

def edit_18(bib):
    # 18. BIBLIOGRAPHIC - Delete field 910 - No conditions
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        bib.delete_field('910')

    return bib

def edit_19(bib):
    # 19. BIBLIOGRAPHIC - Delete field 920 - No condition
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        bib.delete_field('920')

    return bib

#def edit_20(bib):
#    # 20. BIBLIOGRAPHIC - Delete field 949 - TO COMPLETE AFTER DECISION
#    bib.delete_field('949')

def edit_21(bib):
    if bib is None:
        raise Exception('wtf')
    
    # 21. BIBLIOGRAPHIC - Delete field 955 - No condition
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        bib.delete_field('955')

    return bib

def edit_22(bib):
    # 22. BIBLIOGRAPHIC - Delete field 995 - No condition
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        bib.delete_field('995')

    return bib

def edit_23_42(bib):
    # 23. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 022 - No condition
    # 24. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 041 - No conditions
    # 25. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 239 - No conditions
    # 26. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 245 - No conditions
    # 27. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 246 - No conditions
    # 28. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 505 - No conditions
    # 29. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 520 - No conditions
    # 30. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 597 - No conditions
    # 31. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 600 - No conditions
    # 32. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 610 - No conditions
    # 33. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 611 - No conditions
    # 34. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 630 - No conditions
    # 35. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 650 - No conditions
    # 36. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 700 - No conditions
    # 37. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 710 - No conditions
    # 38. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 711 - No conditions
    # 39. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 730 - No conditions
    # 40. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 767 - No conditions
    # 41. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 780 - No conditions
    # 42. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 830 - No conditions
    tags = ('022', '041', '239', '245', '246', '505', '520', '597', '600', '610', '611', '630', '650', '700', '710', '711', '730', '767', '780', '830')
    
    for tag in tags:
        for field in bib.get_fields(tag):
            field.ind1, field.ind2 =  ' ', ' '

    return bib

def edit_43(bib):
    # 43. BIBLIOGRAPHIC, SPEECHES, VOTING - Delete subfield 040 $b - No conditions
    for field in bib.get_fields('040'):
        field.subfields = [x for x in field.subfields if x.code != 'b']

    return bib

def edit_44(bib):
    # 44. BIBLIOGRAPHIC - Delete subfield 079 $q - No condition
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for field in bib.get_fields('079'):
            field.subfields = [x for x in field.subfields if x.code != 'q']

    return bib

def edit_45(bib):
    # 45. BIBLIOGRAPHIC, SPEECHES, VOTING - Delete subfield 089 $a - IF 089__a IS NOT "veto"
    for field in bib.get_fields('089'):
        field.subfields = [x for x in field.subfields if not (x.code == 'a' and x.value.lower() != 'veto')]

    return bib

def edit_46_53(bib):
    # 46. BIBLIOGRAPHIC - Delete subfield 099 $q - No condition
    # 47. BIBLIOGRAPHIC - Delete subfield 191 $f - No condition
    # 48. BIBLIOGRAPHIC - Delete subfield 250 $b - No condition
    # 49. BIBLIOGRAPHIC - Delete subfield 600 $2 - No condition
    # 50. BIBLIOGRAPHIC - Delete subfield 610 $2 - No condition
    # 51. BIBLIOGRAPHIC - Delete subfield 611 $2 - No condition
    # 52. BIBLIOGRAPHIC - Delete subfield 630 $2 - No condition
    # 53. BIBLIOGRAPHIC - Delete subfield 650 $2 - No condition
    pairs = [('099', 'q'), ('191', 'f'), ('250', 'b'), ('600', '2'), ('610', '2'), ('611', '2'), ('630', '2'), ('650', '2')]

    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for tag, code in pairs:
            for field in bib.get_fields(tag):
                field.subfields = [x for x in field.subfields if x.code != code]

    return bib

def edit_54(bib):
    # 54. BIBLIOGRAPHIC, SPEECHES - Delete subfield 710 $9 - No conditions
    if not any([x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for field in bib.get_fields('710'):
            field.subfields = [x for x in field.subfields if x.code != '9']
    
    return bib

###

if __name__ == '__main__':
    run()