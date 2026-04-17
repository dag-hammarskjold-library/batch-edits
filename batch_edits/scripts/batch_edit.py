"""Run a series of specified edits on a set of DLX records"""

import sys, os, re, json, inspect, time, copy
from argparse import ArgumentParser
from datetime import datetime
from pytz import timezone
from batch_edits.module import Class # rename package, module and class
from dlx import DB
from dlx.marc import BibSet, Bib, Auth, Datafield, Diff, Query, Condition, InvalidAuthXref

USER = 'batch_edit_' + str(int(time.time()))
OUT = None

def reimport_and_find_invalid_xrefs(record, tag=None):
    """Refresh linked values from auth records and report unresolved xrefs.

    Returns a list of tuples: (tag, subfield_code, xref).
    """
    invalid = []
    seen = set()

    for field in record.datafields:
        if tag and field.tag != tag:
            continue

        # Always attempt a refresh first so any stale linked values are updated.
        _reimport_subfields_from_auth(field)

        for sub in field.subfields:
            xref = getattr(sub, 'xref', None)

            if not xref:
                continue

            key = (field.tag, sub.code, xref)

            if key in seen:
                continue

            seen.add(key)

            if not Auth.from_query({'_id': xref}, projection={'_id': 1}):
                invalid.append(key)

    return invalid

def _commit_with_reimport_retry(bib, last_edit):
    """Commit once, and retry after xref re-import if invalid auth xrefs are hit."""
    try:
        bib.commit(user=USER)
        return
    except InvalidAuthXref:
        invalid_xrefs = reimport_and_find_invalid_xrefs(bib)

        if invalid_xrefs:
            details = '; '.join([f'{tag}${code} xref={xref}' for tag, code, xref in invalid_xrefs])
            raise Exception(f'Record {bib.id}: commit failed after {last_edit}; invalid xref(s): {details}')

        # InvalidAuthXref was raised, but re-import resolved links; retry commit once.
        try:
            bib.commit(user=USER)
            return
        except Exception as e:
            raise Exception(f'Record {bib.id}: commit failed after {last_edit}; original error: {e}') from e
    except Exception as e:
        invalid_xrefs = reimport_and_find_invalid_xrefs(bib)

        if invalid_xrefs:
            details = '; '.join([f'{tag}${code} xref={xref}' for tag, code, xref in invalid_xrefs])
            raise Exception(f'Record {bib.id}: commit failed after {last_edit}; invalid xref(s): {details}; original error: {e}') from e

        raise Exception(f'Record {bib.id}: commit failed after {last_edit}; original error: {e}') from e

def get_args():
    parser = ArgumentParser()
    parser.add_argument('--connect', required=True, help='DLX connection string')
    parser.add_argument('--database', help='The database name')
    parser.add_argument('--query', help='JSON MDB query document')
    parser.add_argument('--querystring', help='DLX query string')
    parser.add_argument('--limit', type=int, default=0, help='limit the number of records processed')
    parser.add_argument('--output', required=True, choices=['db', 'mrk'], help='')
    parser.add_argument('--output_file', help='File to write output to if output is mrk')
    parser.add_argument('--skip_confirm', action='store_true', help='')
    parser.add_argument('--view_changes', action='store_true', help='')
    parser.add_argument('--initials', help='Initials to use for the 999 field (default: js)')

    return parser.parse_args()

def run(**kwargs):
    if kwargs:
        sys.argv = [sys.argv[0]]
        
        for param, arg in kwargs.items():
            sys.argv.append(f'--{param}' if isinstance(arg, bool) else f'--{param}={arg}')

    args = get_args()

    if DB.database_name == 'testing':
        # let the test module connect to the DB
        pass
    else:
        DB.connect(args.connect, database=args.database)

    if args.output == 'mrk':
        if args.output_file:
            OUT = open(args.output_file, 'w')
        else:
            OUT = sys.stdout

    if args.initials:
        initials = args.initials

    query = Query.from_string(args.querystring) if args.querystring else json.loads(args.query) if args.query else {}
    bibs = BibSet.from_query(query, limit=args.limit)
    edits = [f for name, f in inspect.getmembers(sys.modules[__name__], inspect.isfunction) if name[:5] == 'edit_']
    i, status = 0, ''

    for bib in bibs:
        i += 1

        for field in bib.datafields:
            if field.ind1 == '_':
                field.ind1 = ' '

            if field.ind2 == '_':
                field.ind2 = ' '

        before_edits = copy.deepcopy(bib)

        # Normalize 991 from linked authority 191 before running individual edits.
        _reimport_991_from_linked_auth_191(bib)

        # Re-import and validate linked subfields before the numbered edits run.
        if not _preprocess_linked_subfields_before_edits(bib):
            print(f'--> record id {bib.id}: skipped before edits (linked subfield precheck failed)')
            continue

        last_edit = None

        for edit in edits:
            last_edit = edit.__name__

            try:
                bib = edit(bib)
            except Exception as e:
                raise Exception(f'Record {bib.id}: failed during {last_edit}: {e}') from e

            if not isinstance(bib, Bib):
                raise Exception('Edit function not returning a Bib object')
        
        initials = args.initials if args.initials else 'js'
        if len(initials) > 2:
            initials = initials[:2]
        bib = add_999(bib, initials)
            
        if changes := '\n'.join([f.to_mrk() for f in Diff(before_edits, bib).a]):
            if args.view_changes:
                if args.output == 'mrk':
                    OUT.write(f'--> record id {bib.id}\nFields changed:\n{changes}\n\nRecord with changes:\n')
                else:
                    print(f'--> record id {bib.id}\nFields changed:\n{changes}\n\nRecord with changes:\n')

            if args.output == 'mrk':
                OUT.write(bib.to_mrk() + '\n')
            elif args.output == 'db':
                if args.skip_confirm:
                    _commit_with_reimport_retry(bib, last_edit)

                    status = ('\b' * len(status)) + f'Records updated: {i}'
                    print(status, end='', flush=True)
                else:
                    x = input(f'{bib.to_mrk()}\nCommit changes? (y/n): ')

                    if x.lower() != 'y':
                        print('Changes disregarded\n')
                        time.sleep(1)
                        continue

                    _commit_with_reimport_retry(bib, last_edit)

                    print(f'OK. Updated {bib.id}\n')
                    time.sleep(1)
        else:
            print(f'--> record id {bib.id}: No changes')

###

# delete_field
def edit_1(bib):
    # 1. BIBLIOGRAPHIC - Delete field 099 - IF subfield c is empty OR if subfield c = internet
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        [bib.delete_field(field) for field in bib.get_fields('099') if field.get_value('c').lower() == 'internet']
        [bib.delete_field(field) for field in bib.get_fields('099') if not field.get_value('c')]

    return bib

# delete_field   
def edit_2(bib):
    # 2. BIBLIOGRAPHIC - Delete field 029 - IF subfield a IS NOT JN or UN
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        [bib.delete_field(field) for field in bib.get_fields('029') if field.get_value('a') not in ('JN', 'UN')]

    return bib

# delete_field
def edit_3(bib):
    # 3. BIBLIOGRAPHIC, SPEECHES, VOTING - Delete field 930 - If NOT 930:UND* OR 930:UNGREY* OR 930:CIF* OR 930:DIG* OR 930:HUR* OR 930:PER* OR 930:PN*
    for field in bib.get_fields('930'):
        if not any([re.match(f'^{x}', field.get_value('a')) for x in ('UND', 'UNP', 'UNGREY', 'CIF', 'DIG', 'HUR', 'PER', 'PN')]):
            bib.fields = [f for f in bib.fields if f != field] # todo: fix dlx.Marc.delete_field with field as arg # 2025-11-4 this may be done?

    return bib  

# delete_field        
def edit_4(bib):
    # 4. BIBLIOGRAPHIC, SPEECHES, VOTING - Delete field 000 - No condition
    bib.delete_fields('000')
    return bib

# delete_field
def edit_5(bib):
    # 5. BIBLIOGRAPHIC - Delete field 008 - No condition
    # update: delete for all record types
    
    bib.delete_fields('008')

    return bib

# delete_field
def edit_6(bib):
    # 6. BIBLIOGRAPHIC, VOTING - Delete field 035 - IF 089__b is NOT B22 (keep 035 for speeches)
    if not any([x == 'Speeches' for x in bib.get_values('989', 'a')]):
        bib.delete_fields('035')

    return bib

# delete_field
def edit_7(bib):
    # 7. BIBLIOGRAPHIC - Delete field 069 - No condition
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        bib.delete_fields('069')

    return bib

# change_tag
def edit_8_9_10_11_14(bib):
    # 8. BIBLIOGRAPHIC - Transfer field 100 - to 700 - Clean indicators before transfer
    # 9. BIBLIOGRAPHIC - Transfer field 110 - to 710 - Clean indicators before transfer
    # 10. BIBLIOGRAPHIC - Transfer field 111 - to 711 - Clean indicators before transfer
    # 11. BIBLIOGRAPHIC - Transfer field 130 - to 730 - Clean indicators before transfer
    # 14. BIBLIOGRAPHIC - Transfer field 440 - To 830 - Clean indicators before transfer
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for from_tag, to_tag in [('100', '700'), ('110', '710'), ('111', '711'), ('130', '730'), ('440', '830')]:
            for field in bib.get_fields(from_tag):
                field.ind1, field.ind1 = ' ', ' '

            bib = change_tag(bib, from_tag, to_tag)

    return bib

# delete_field
def edit_12(bib):
    # 12. BIBLIOGRAPHIC - Delete field 222 - No condition
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        bib.delete_fields('222')

    return bib

# delete_field
def edit_13(bib):
    # 13. VOTING, SPEECHES - Delete field 269 - If (089:B22 OR  089:B23) - Only speeches and votes
    if any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        bib.delete_fields('269')

    return bib

# no function
def edit_15(bib):
    # 15. BIBLIOGRAPHIC - Transfer field 490 $x - Transfer to 022 $a if the field with the same value does not exists
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for field in bib.get_fields('490'):
            val = field.get_value('x')

            if val not in bib.get_values('022', 'a'):
                bib.set('022', 'a', val, address='+')
            
            field.subfields = [s for s in field.subfields if s.code != 'x']

    return bib

# delete_field
def edit_16(bib):
    # 16. BIBLIOGRAPHIC - Delete field 597 - If 597:"Retrospective indexing"

    # skip for now
    return bib

    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for field in bib.get_fields('597'):
            if field.get_value('a').lower()[:22] == 'retrospective indexing':
                bib.delete_field(field)

    return bib

# delete_field
def edit_17(bib):
    # 17. BIBLIOGRAPHIC - Delete field 773 - No condition
    # amendment: move to 580
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for field in bib.get_fields('773'):
            field.ind1, field.ind2 = ' ', ' '
            field.tag = '580'

        bib.delete_fields('773')

    return bib

# delete_field
def edit_18(bib):
    # 18. BIBLIOGRAPHIC - Delete field 910 - No conditions
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        bib.delete_fields('910')

    return bib

# delete_field
def edit_19(bib):
    # 19. BIBLIOGRAPHIC - Delete field 920 - No condition
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        bib.delete_fields('920')

    return bib

# delete_field
def edit_20(bib):
    # 20. BIBLIOGRAPHIC - Delete field 949 - TO COMPLETE AFTER DECISION
    # update: go ahead
    bib.delete_fields('949')

    return bib

# delete_field
def edit_21(bib):
    # 21. BIBLIOGRAPHIC - Delete field 955 - No condition
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        bib.delete_fields('955')

    return bib

# delete_field
def edit_22(bib):
    # 22. BIBLIOGRAPHIC - Delete field 995 - No condition
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        bib.delete_fields('995')

    return bib

# delete_indicators
def edit_23_34_36_42(bib):
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
    # 36. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 700 - No conditions
    # *DISABLED* 35. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 650 - No conditions
    # 37. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 710 - No conditions
    # 38. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 711 - No conditions
    # 39. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 730 - No conditions
    # 40. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 767 - No conditions
    # 41. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 780 - No conditions
    # 42. BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 830 - No conditions
    # 43.1 BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 740 - No conditions
    # 43.2 BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 785 - No conditions
    # 43.3 BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 362 - No conditions
    # 43.4 BIBLIOGRAPHIC, VOTING, SPEECHES - Delete indicators 490 - No conditions
    tags = ('022', '041', '239', '245', '246', '362', '490', '505', '520', '597', '600', '610', '611', '630', '700', '710', '711', '730', '740', '767', '780', '785', '830')
    
    for tag in tags:
        for field in bib.get_fields(tag):
            field.ind1 = ' ' if field.ind1 not in (' ', '_') else field.ind1
            field.ind2 = ' ' if field.ind2 not in (' ', '_') else field.ind2

    return bib

# delete_subfield
def edit_43(bib):
    # 43. BIBLIOGRAPHIC, SPEECHES, VOTING - Delete subfield 040 $b - No conditions
    for field in bib.get_fields('040'):
        field.subfields = [x for x in field.subfields if x.code != 'b']

    return bib

# delete_subfield
def edit_44(bib):
    # 44. BIBLIOGRAPHIC - Delete subfield 079 $q - No condition
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for field in bib.get_fields('079'):
            field.subfields = [x for x in field.subfields if x.code != 'q']

    return bib

# delete_subfield
def edit_45(bib):
    # 45. BIBLIOGRAPHIC, SPEECHES, VOTING - Delete subfield 089 $a - IF 089__a IS NOT "veto"
    for field in bib.get_fields('089'):
        field.subfields = [x for x in field.subfields if not (x.code == 'a' and x.value.lower() != 'veto')]

    return bib

# delete_subfield
def edit_46_53(bib):
    # 46. BIBLIOGRAPHIC - Delete subfield 099 $q - No condition
    # 47. BIBLIOGRAPHIC - Delete subfield 191 $f - No condition
    # 49. BIBLIOGRAPHIC - Delete subfield 600 $2 - No condition
    # 50. BIBLIOGRAPHIC - Delete subfield 610 $2 - No condition
    # 51. BIBLIOGRAPHIC - Delete subfield 611 $2 - No condition
    # 52. BIBLIOGRAPHIC - Delete subfield 630 $2 - No condition
    # 53. BIBLIOGRAPHIC - Delete subfield 650 $2 - No condition
    # 53.1 BIBLIOGRAPHIC - Delete subfield 041 $b - No condition
    # 53.2 BIBLIOGRAPHIC - Delete subfield 520 $b - No condition
    # 53.3 BIBLIOGRAPHIC - Delete subfield 520 $9 - No condition
    pairs = [('041', 'b'), ('099', 'q'), ('191', 'f'), ('250', 'b'), ('520', 'b'), ('520', '9'), ('600', '2'), ('610', '2'), ('611', '2'), ('630', '2'), ('650', '2')]

    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for tag, code in pairs:
            for field in bib.get_fields(tag):
                field.subfields = [x for x in field.subfields if x.code != code]

    return bib

# no function
def edit_48(bib):
    # 48. BIBLIOGRAPHIC - Delete subfield 250 $b - No condition
    # need to strip the = at the end of subfield $a
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for field in bib.get_fields('250'):
            if field.get_subfield('b'):
                field.subfields = [x for x in field.subfields if x.code != 'b']

                if field.get_subfield('a').value[-1] == '=':
                    field.get_subfield('a').value = field.get_subfield('a').value[:-1]

    return bib

# delete_subfield
def edit_54(bib):
    # 54. BIBLIOGRAPHIC, SPEECHES - Delete subfield 710 $9 - No conditions
    if not any([x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        for field in bib.get_fields('710'):
            field.subfields = [x for x in field.subfields if x.code != '9']
    
    return bib

def edit_55(bib):
    # NEW: BIBLIOGRAPHIC, VOTING, SPEECHES, BIBLIOGRAPHIC - Delete indicators 650 - if 269$a < 2014 delete ind2 else delete both
    date = bib.get_value('269', 'a')

    try:
        int_date = int(date[:4])
    except ValueError:
        int_date = None

    for field in bib.get_fields('650'):
        if int_date and int_date < 2014:
            field.ind2 = ' '
        else:
            field.ind1 = ' '
            field.ind2 = ' '

    return bib

# delete field
def edit_56(bib):
    # NEW: BIBLIOGRAPHIC - Delete field 529 - no condition
    if not any([x == 'Speeches' or x == 'Voting Data' for x in bib.get_values('989', 'a')]):
        bib.delete_fields('529')

    return bib

def _reimport_subfields_from_auth(field, include_non_none=False):
    """Repopulate subfield values from linked authority records.

    By default only subfields with value None are updated. Set
    include_non_none=True to refresh all linked subfields with available
    authority values.
    """
    xrefs_in_field = [sub.xref for sub in field.subfields if hasattr(sub, 'xref')]
    fallback_xref = xrefs_in_field[0] if xrefs_in_field else None

    for sub in field.subfields:
        if sub.value is not None and not include_non_none:
            continue

        xref = getattr(sub, 'xref', None) or fallback_xref

        if not xref:
            continue

        looked_up = Auth.lookup(xref, sub.code)

        if looked_up is not None:
            try:
                sub.value = looked_up
            except AttributeError:
                # Linked subfields can be immutable; keep their resolved value.
                pass

def _reimport_tag_and_validate_required_subfield(
    bib,
    tag,
    required_subfield_code,
    edit_name,
    drop_none_if_auth_missing_required=False,
):
    """Re-import linked values for a tag and ensure required subfield isn't None."""
    def _lookup_required(sub):
        xref = getattr(sub, 'xref', None)
        return Auth.lookup(xref, required_subfield_code) if xref else None

    invalid_xrefs = reimport_and_find_invalid_xrefs(bib, tag=tag)

    if invalid_xrefs:
        xrefs = sorted({xref for _, _, xref in invalid_xrefs})
        print(
            f"--> record id {bib.id}: {edit_name} skipped "
            f"(invalid xref(s) in {tag}: {', '.join(map(str, xrefs))})"
        )
        return False

    for field in bib.get_fields(tag):
        _reimport_subfields_from_auth(field)

        none_required = [
            x for x in field.subfields if x.code == required_subfield_code and x.value is None
        ]

        unresolved_required = [
            x
            for x in field.subfields
            if x.code == required_subfield_code
            and hasattr(x, 'xref')
            and getattr(x, 'xref', None)
            and _lookup_required(x) is None
        ]

        if drop_none_if_auth_missing_required and (none_required or unresolved_required):
            xrefs_in_field = [x.xref for x in field.subfields if hasattr(x, 'xref') and getattr(x, 'xref', None)]
            fallback_xref = xrefs_in_field[0] if xrefs_in_field else None
            linked_auth_missing_required = True

            for sub in none_required:
                xref = getattr(sub, 'xref', None) or fallback_xref

                if xref and Auth.lookup(xref, required_subfield_code) is not None:
                    linked_auth_missing_required = False
                    break

            if linked_auth_missing_required:
                _reimport_subfields_from_auth(field, include_non_none=True)
                field.subfields = [
                    x
                    for x in field.subfields
                    if not (
                        x.code == required_subfield_code
                        and (
                            x.value is None
                            or (
                                hasattr(x, 'xref')
                                and getattr(x, 'xref', None)
                                and _lookup_required(x) is None
                            )
                        )
                    )
                ]

        if drop_none_if_auth_missing_required and any(
            x.code == required_subfield_code
            and hasattr(x, 'xref')
            and getattr(x, 'xref', None)
            and _lookup_required(x) is None
            for x in field.subfields
        ):
            print(
                f'--> record id {bib.id}: {edit_name} skipped '
                f'({tag}${required_subfield_code} has unresolved linked xref after re-validation)'
            )
            return False

        if any(
            x.code == required_subfield_code and x.value is None
            for x in field.subfields
        ):
            print(
                f'--> record id {bib.id}: {edit_name} skipped '
                f'({tag}${required_subfield_code} still None after xref re-validation)'
            )
            return False

    return True

def _preprocess_linked_subfields_before_edits(bib):
    """Apply linked-subfield re-import/validation before numbered edits."""
    checks = [
        ('600', 'g', True),
        ('610', 'g', True),
        ('700', 'g', True),
        ('611', 'g', True),
        ('611', 'a', False),
        ('191', 'c', False),
    ]

    for tag, required_subfield_code, drop_none_if_missing in checks:
        if not _reimport_tag_and_validate_required_subfield(
            bib,
            tag,
            required_subfield_code,
            'pre-edit',
            drop_none_if_auth_missing_required=drop_none_if_missing,
        ):
            return False

    return True

def _reimport_991_from_linked_auth_191(bib):
    """Replace 991 fields with values copied from linked authority 191 fields."""
    xrefs = []

    for field in bib.get_fields('991'):
        for sub in field.subfields:
            if hasattr(sub, 'xref') and sub.xref not in xrefs:
                xrefs.append(sub.xref)

    bib.delete_fields('991')

    for xref in xrefs:
        auth = Auth.from_query({'_id': xref})

        if not auth:
            continue

        auth_191 = auth.get_field('191')

        if not auth_191:
            continue

        new_field = Datafield('991', record_type='bib')

        for sub in auth_191.subfields:
            if sub.code == '0' or sub.value is None:
                continue

            new_field.set(sub.code, xref)

        #if not new_field.get_subfield('0'):
        #    new_field.set('0', str(xref))

        if new_field.subfields:
            bib.fields.append(new_field)

    return bib

def edit_57(bib):
    # BIBLIOGRAPHIC - Re-import None subfield values via xref before logging/skipping
    for tag in ('600', '610', '700'):
        if not _reimport_tag_and_validate_required_subfield(
            bib,
            tag,
            'g',
            'edit_57',
            drop_none_if_auth_missing_required=True,
        ):
            return bib

    return bib

def edit_58(bib):
    # BIBLIOGRAPHIC - Re-import None subfield values via xref before logging/skipping
    if not _reimport_tag_and_validate_required_subfield(
        bib,
        '611',
        'g',
        'edit_58',
        drop_none_if_auth_missing_required=True,
    ):
        return bib

    if not _reimport_tag_and_validate_required_subfield(bib, '611', 'a', 'edit_58'):
        return bib

    return bib

def edit_59(bib):
    # BIBLIOGRAPHIC - Re-import None subfield values via xref before logging/skipping
    if not _reimport_tag_and_validate_required_subfield(bib, '191', 'c', 'edit_59'):
        return bib

    return bib

# add 999
'''
Takes the 999 addition out of the regular edits so that initials can be passed in from command line
'''
def add_999(bib, initials='js'):
    # NEW: ALL - Add 999
    date = datetime.now().astimezone(timezone('US/Eastern')).strftime(r'%Y%m%d')
    field = Datafield('999', record_type='bib')
    field.set('a', f'{initials}b{date}').set('b', date).set('c', 'b')
    bib.fields.append(field)

    return bib

### future - abstracted functions

def change_value():
    pass

def delete_field(record, tag, conditions=[]):
    if conditions:
        assert all([isinstance(c, Condition) for c in conditions])

        for field in record.get_fields(tag):
            for subfields in [x.subfields for x in conditions]:
                for code, val in subfields:
                    if val in field.get_values(code):
                        record.delete_field(field)
    else:
        record.delete_field(tag)

    return record

def change_tag(record, from_tag, to_tag, conditions=[]):
        assert all([isinstance(c, Condition) for c in conditions]) if conditions else True

        for field in record.get_fields(from_tag):
            if conditions:
                for subfields in [x.subfields for x in conditions]:
                    for code, val in subfields:
                        if val in field.get_values(code):
                            field.tag = to_tag
            else:
                field.tag = to_tag

        return record

def delete_indicators(record, tag, conditions=[]):
    if conditions:
        assert all([isinstance(c, Condition) for c in conditions])

        for field in record.get_fields(tag):
            for subfields in [x.subfields for x in conditions]:
                for code, val in subfields:
                    if val in field.get_values(code):
                        field.ind1, field.ind2 = [' ', ' ']

    return record

def delete_subfield(record, tag, subfield_code, conditions=[]):
    if conditions:
        assert all([isinstance(c, Condition) for c in conditions])

        for field in record.get_fields(tag):
            for subfields in [x.subfields for x in conditions]:
                for code, val in subfields:
                    if val in field.get_values(code):
                        field.subfields = [x for x in field.subfields if code != subfield_code]

    return record

def delete_indicators():
    pass

def change_indicators():
    pass

###

if __name__ == '__main__':
    run()