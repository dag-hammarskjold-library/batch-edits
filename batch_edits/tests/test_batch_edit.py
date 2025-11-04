import sys, pytest, random
from datetime import datetime
from pytz import timezone
from dlx import DB
from dlx.marc import Bib, Auth, BibSet, AuthSet, Query, Condition
from batch_edits.scripts import batch_edit

DB.connect('mongomock://localhost')

defaults = [Bib() for i in range(0, 10)]
speeches = [Bib().set('989', 'a', 'Speeches') for i in range(0, 10)]
votes = [Bib().set('989', 'a', 'Voting Data') for i in range(0, 10)]
def all_records(): return defaults + speeches + votes

def test_script_runs(bibs):
    batch_edit.run(connect='mongomock://localhost', output='db', skip_confirm=True, limit=30)
    bibs = BibSet.from_query({})
    assert bibs.count == 30

    # records have no data, no edits made
    assert all([bib.user == 'testing' for bib in bibs])

    # test changes are committed
    [bib.set('710', '9', 'dummy') and bib.commit() for bib in BibSet.from_query({})]
    batch_edit.run(connect='mongomock://localhost', output='db', skip_confirm=True)
    assert all([bib.user[:10] == 'batch_edit' for bib in BibSet.from_query({})])
    
def test_edit_1():
    # 1. BIBLIOGRAPHIC - Delete field 099 if subfield c = internet
    [bib.set('099', 'c', 'internet') for bib in all_records()]
    [bib.set('099', 'a', 'other') for bib in defaults]
    assert len([bib.get_value('099', 'c') == 'internet' for bib in defaults]) == 10
    [batch_edit.edit_1(x) for x in all_records()]
    assert not any([bib.get_value('099', 'c') == 'internet' for bib in defaults])
    assert all([bib.get_value('099', 'c') == 'internet' for bib in speeches + votes])

def test_edit_2():
    # 2. BIBLIOGRAPHIC - Delete field 029 - IF subfield a IS NOT JN or UN
    [bib.set('029', 'a', 'JN' if i < 2 else 'UN' if i < 5 else 'to delete') for i, bib in enumerate(defaults)]
    [bib.set('029', 'a', 'other') for bib in speeches + votes]
    assert len([bib for bib in defaults if bib.get_value('029', 'a') == 'to delete']) == 5
    [batch_edit.edit_2(bib) for bib in all_records()]
    assert len([bib for bib in defaults if bib.get_value('029', 'a') == 'to delete']) == 0
    assert len([bib for bib in defaults if bib.get_value('029', 'a') in ('JN', 'UN')]) == 5
    assert all([bib.get_value('029', 'a') == 'other' for bib in speeches + votes])

def test_edit_3():
    # 3. BIBLIOGRAPHIC, SPEECHES, VOTING - Delete field 930 - If NOT 930:UND* OR 930:UNGREY* OR 930:CIF* OR 930:DIG* OR 930:HUR*  oR 930:PER*
    # ?subfield $a?
    values = ['UND', 'UNP', 'UNGREY', 'CIF', 'DIG', 'HUR', 'PER', 'PN']
    values = values + values + [random.choice(values) for x in range(4)]                          # make the array 20 elements using all the values to keep
    [bib.set('930', 'a', values[i]) for i, bib in enumerate(all_records()[:20])]                  # 20 records have fields to keep
    [bib.set('930', 'a', 'other') for bib in all_records()[20:]]                                  # 10 records have fields to delete     
    assert len([bib for bib in all_records() if bib.get_value('930', 'a') == 'other']) == 10
    [batch_edit.edit_3(bib) for bib in all_records()]
    assert len([bib for bib in all_records() if bib.get_value('930', 'a') == 'other']) == 0
    assert len([bib for bib in all_records() if bib.get_value('930', 'a') in values]) == 20

def test_edit_4():
    # 4. BIBLIOGRAPHIC, SPEECHES, VOTING - Delete field 000 - No condition
    [bib.set('000', None, 'to delete') for bib in all_records()]
    assert all([bib.get_value('000') for bib in all_records()])
    [batch_edit.edit_4(bib) for bib in all_records()]
    assert not any([bib.get_value('000') for bib in all_records()])

def test_edit_5():
    # 5. BIBLIOGRAPHIC - Delete field 008 - No condition
    [bib.set('008', None, 'dummy') for bib in all_records()]
    assert all([bib.get_value('008') for bib in all_records()])
    [batch_edit.edit_5(bib) for bib in all_records()]
    assert not any([bib.get_value('008') for bib in all_records()])

def test_edit_6():
    # 6. BIBLIOGRAPHIC, VOTING - Delete field 035 - IF 089__b is NOT B22 (keep 035 for speeches)
    [bib.set('035', 'a', 'dummy') for bib in all_records()]
    assert all([bib.get_value('035', 'a') for bib in all_records()])
    [batch_edit.edit_6(bib) for bib in all_records()]
    assert not any([bib.get_value('035', 'a') for bib in defaults + votes])
    assert all([bib.get_value('035', 'a') for bib in speeches])

def test_edit_7():
    # 7. BIBLIOGRAPHIC - Delete field 069 - No condition
    [bib.set('069', 'a', 'dummy').set('069', 'b', 'dummy2', address=['+']) for bib in all_records()]
    print('\n'.join([x.to_mrk() for x in all_records()]))
    assert all([bib.get_value('069', 'a') for bib in all_records()])
    assert all([bib.get_values('069', 'b') for bib in all_records()])
    [batch_edit.edit_7(bib) for bib in all_records()]
    assert not any([bib.get_value('069', 'a') for bib in defaults])
    assert not any([bib.get_value('069', 'b') for bib in defaults])
    assert all([bib.get_value('069', 'a') for bib in speeches + votes])

def test_edit_8_9_10_11_14():
    # 8. BIBLIOGRAPHIC - Transfer field 100 - to 700 - Clean indicators before transfer
    # 9. BIBLIOGRAPHIC - Transfer field 110 - to 710 - Clean indicators before transfer
    # 10. BIBLIOGRAPHIC - Transfer field 111 - to 711 - Clean indicators before transfer
    # 11. BIBLIOGRAPHIC - Transfer field 130 - to 730 - Clean indicators before transfer
    # 14. BIBLIOGRAPHIC - Transfer field 440 - To 830 - Clean indicators before transfer
    Auth().set('100', 'a', 'dummy').commit()
    [bib.set('100', 'a', 'dummy') for bib in all_records()]
    [setattr(bib.get_field('100'), 'ind1', 9) for bib in all_records()]
    assert all([bib.get_value('100', 'a') for bib in all_records()])
    assert all([bib.get_field('100').ind1 for bib in defaults])
    [batch_edit.edit_8_9_10_11_14(bib) for bib in all_records()]
    assert not any([bib.get_value('100', 'a') for bib in defaults])
    assert all([bib.get_value('700', 'a') for bib in defaults])
    assert all([bib.get_field('700').ind1 == ' ' for bib in defaults])
    assert all([bib.get_value('100', 'a') for bib in speeches + votes])

def test_edit_12():
    # 12. BIBLIOGRAPHIC - Delete field 222 - No condition
    [bib.set('222', 'a', 'dummy') for bib in all_records()]
    assert all([bib.get_value('222', 'a') for bib in all_records()])
    [batch_edit.edit_12(bib) for bib in all_records()]
    assert not any([bib.get_value('222', 'a') for bib in defaults])
    assert all([bib.get_value('222', 'a') for bib in speeches + votes])

def test_edit_13():
    # 13. VOTING, SPEECHES - Delete field 269 - If (089:B22 OR  089:B23) - Only speeches and votes
    [bib.set('269', 'a', 'dummy') for bib in all_records()]
    assert all([bib.get_value('269', 'a') for bib in all_records()])
    [batch_edit.edit_13(bib) for bib in speeches + votes]
    assert not any([bib.get_value('269', 'a') for bib in speeches + votes])
    assert all([bib.get_value('269', 'a') for bib in defaults])

def test_edit_15():
    # 15. BIBLIOGRAPHIC - Transfer field 490 $x - Transfer to 022 $a if the field with the same value does not exists
    [bib.set('490', 'x', 'dummy') for bib in all_records()]
    [bib.set('022', 'a', 'dummy') for bib in defaults[:5]]
    [bib.set('022', 'a', 'other') for bib in defaults[5:]]
    assert len([bib for bib in all_records() if bib.get_value('490', 'x')]) == 30
    assert len([bib for bib in defaults if bib.get_value('022', 'a') == 'dummy']) == 5
    [batch_edit.edit_15(bib) for bib in all_records()]
    assert len([bib for bib in all_records() if bib.get_value('490', 'x')]) == 20
    assert len([bib for bib in defaults if bib.get_value('022', 'a')]) == 10
    assert len([bib for bib in defaults if bib.get_value('022', 'a') == 'other']) == 5
    assert len([bib for bib in speeches + votes if bib.get_value('022', 'a')]) == 0

@pytest.mark.skip()
def test_edit_16():
    # 16. BIBLIOGRAPHIC - Delete field 597 - If 597:"Retrospective indexing"
    [bib.set('597', 'a', 'Retrospective indexing.') for bib in all_records()]
    assert all([bib.get_value('597', 'a') == 'Retrospective indexing.' for bib in all_records()])
    [batch_edit.edit_16(bib) for bib in all_records()]
    assert not any([bib.get_value('597', 'a') == 'Retrospective indexing.' for bib in defaults])
    assert all([bib.get_value('597', 'a') == 'Retrospective indexing.' for bib in speeches + votes])

def test_edit_17():
    # 17. BIBLIOGRAPHIC - Delete field 773 - No condition
    [bib.set('773', 'a', 'dummy') for bib in all_records()]
    assert all([bib.get_value('773', 'a') for bib in all_records()])
    [batch_edit.edit_17(bib) for bib in all_records()]
    assert not any([bib.get_value('773', 'a') for bib in defaults])
    assert all(['dummy' in bib.get_values('580', 'a') for bib in defaults])
    assert all([bib.get_value('773', 'a') for bib in speeches + votes])

def test_edit_18():
    # 18. BIBLIOGRAPHIC - Delete field 910 - No conditions
    [bib.set('910', 'a', 'dummy') for bib in all_records()]
    assert all([bib.get_value('910', 'a') for bib in all_records()])
    [batch_edit.edit_18(bib) for bib in all_records()]
    assert not any([bib.get_value('910', 'a') for bib in defaults])
    assert all([bib.get_value('910', 'a') for bib in speeches + votes])

def test_edit_19():
    # 19. BIBLIOGRAPHIC - Delete field 920 - No condition
    [bib.set('920', 'a', 'dummy') for bib in all_records()]
    assert all([bib.get_value('920', 'a') for bib in all_records()])
    [batch_edit.edit_19(bib) for bib in all_records()]
    assert not any([bib.get_value('920', 'a') for bib in defaults])
    assert all([bib.get_value('920', 'a') for bib in speeches + votes])

#@pytest.mark.skip(reason='Not implemented yet')
def test_edit_20():
    # 20. BIBLIOGRAPHIC - Delete field 949 - TO COMPLETE AFTER DECISION
    [bib.set('949', 'a', 'dummy') for bib in all_records()]
    assert all([bib.get_value('949', 'a') for bib in all_records()])
    [batch_edit.edit_20(bib) for bib in all_records()]
    assert not any([bib.get_value('949', 'a') for bib in all_records()])
    #assert all([bib.get_value('949', 'a') for bib in speeches + votes])

def test_edit_21():
    # 21. BIBLIOGRAPHIC - Delete field 955 - No condition
    [bib.set('955', 'a', 'dummy') for bib in all_records()]
    assert all([bib.get_value('955', 'a') for bib in all_records()])
    [batch_edit.edit_21(bib) for bib in all_records()]
    assert not any([bib.get_value('955', 'a') for bib in defaults])
    assert all([bib.get_value('955', 'a') for bib in speeches + votes])

def test_edit_23_34_36_42():
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
        [bib.set(tag, 'z', 'dummy', ind1='9', ind2='9', address='+') for bib in all_records()]
        assert all([any([field.ind1 == '9' and field.ind2 == '9' for field in bib.get_fields(tag)]) for bib in all_records()])
    
    [batch_edit.edit_23_34_36_42(bib) for bib in all_records()]
    
    for tag in tags:
        assert all([all([field.ind1 == ' ' and field.ind2 == ' ' for field in bib.get_fields(tag)]) for bib in all_records()])

def test_edit_43():
    # 43. BIBLIOGRAPHIC, SPEECHES, VOTING - Delete subfield 040 $b - No conditions
    [bib.set('040', 'b', 'dummy') for bib in all_records()]
    assert all([bib.get_value('040', 'b') for bib in all_records()])
    [batch_edit.edit_43(bib) for bib in all_records()]
    assert not any([bib.get_value('040', 'b') for bib in all_records()])

def test_edit_44():
    # 44. BIBLIOGRAPHIC - Delete subfield 079 $q - No condition
    [bib.set('079', 'q', 'dummy') for bib in all_records()]
    assert all([bib.get_value('079', 'q') for bib in all_records()])
    [batch_edit.edit_44(bib) for bib in all_records()]
    assert not any([bib.get_value('079', 'q') for bib in defaults])
    assert all([bib.get_value('079', 'q') for bib in speeches + votes])

def test_edit_45():
    # 45. BIBLIOGRAPHIC, SPEECHES, VOTING - Delete subfield 089 $a - IF 089__a IS NOT "veto"
    [bib.set('089', 'a', 'veto') for bib in all_records()[:5]]
    [bib.set('089', 'a', 'other') for bib in all_records()[5:]]
    assert len([x for x in all_records() if 'veto' in x.get_values('089', 'a')]) == 5
    assert len([x for x in all_records() if 'other' in x.get_values('089', 'a')]) == 25
    [batch_edit.edit_45(bib) for bib in all_records()]
    assert len([x for x in all_records() if 'veto' in x.get_values('089', 'a')]) == 5
    assert len([x for x in all_records() if 'other' in x.get_values('089', 'a')]) == 0
    
def test_edit_46_53():
    # 46. BIBLIOGRAPHIC - Delete subfield 099 $q - No condition
    # 47. BIBLIOGRAPHIC - Delete subfield 191 $f - No condition
    # 49. BIBLIOGRAPHIC - Delete subfield 600 $2 - No condition
    # 50. BIBLIOGRAPHIC - Delete subfield 610 $2 - No condition
    # 51. BIBLIOGRAPHIC - Delete subfield 611 $2 - No condition
    # 52. BIBLIOGRAPHIC - Delete subfield 630 $2 - No condition
    # 53. BIBLIOGRAPHIC - Delete subfield 650 $2 - No condition
    # 53.1 BIBLIOGRAPHIC - Delete subfield 041 $b - No condition
    # 53.2 BIBLIOGRAPHIC - Delete subfield 520 $b - No condition
    pairs = [('041', 'b'), ('099', 'q'), ('191', 'f'), ('250', 'b'), ('520', 'b'), ('520', '9'), ('600', '2'), ('610', '2'), ('611', '2'), ('630', '2'), ('650', '2')]
    [bib.set(tag, code, 'dummy') for bib in all_records() for tag, code in pairs]
    assert all([bib.get_value(tag, code) for bib in all_records() for tag, code in pairs])
    [batch_edit.edit_46_53(bib) for bib in all_records()]
    assert not any([bib.get_value(tag, code) for bib in defaults for tag, code in pairs])

def test_edit_48():
    # 48. BIBLIOGRAPHIC - Delete subfield 250 $b - No condition
    # need to strip the = at the end of subfield $a
    [bib.set('250', 'a', 'dummy=').set('250', 'b', 'dummy') for bib in all_records()]
    [batch_edit.edit_48(bib) for bib in all_records()]
    assert not any([bib.get_value('250', 'b') for bib in defaults])
    assert not any([bib.get_value('250', 'a')[-1] == '=' for bib in defaults])

def test_edit_54():
    # 54. BIBLIOGRAPHIC, SPEECHES - Delete subfield 710 $9 - No conditions
    [bib.set('710', '9', 'dummy') for bib in all_records()]
    assert all([bib.get_value('710', '9') for bib in all_records()])
    [batch_edit.edit_54(bib) for bib in all_records()]
    assert not any([bib.get_value('710', '9') for bib in defaults + speeches])
    assert all([bib.get_value('710', '9') for bib in votes])

def test_edit_55():
    # NEW: BIBLIOGRAPHIC, VOTING, SPEECHES, BIBLIOGRAPHIC - Delete indicators 650 - if 269$a < 2014 delete ind2 else delete both
    import re

    [bib.set('269', 'a', '2013') for bib in all_records()[:15]]
    [bib.set('269', 'a', '2014') for bib in all_records()[15:]]
    Auth().set('150', 'a', 'OK').commit()
    
    for bib in all_records():
        bib.set('650', 'a', 'OK', ind1='1', ind2='2')

    assert all([re.match('(2013|2014)', bib.get_value('269', 'a')) for bib in all_records()])
    assert len([bib for bib in all_records() if bib.get_fields('650')[0].ind1 == '1']) == 30
    [batch_edit.edit_55(bib) for bib in all_records()]
    assert len([bib for bib in all_records() if bib.get_fields('650')[0].ind1 == '1']) == 15
    assert len([bib for bib in all_records() if bib.get_fields('650')[0].ind2 == '2']) == 0

def test_edit_56():
    # NEW: BIBLIOGRAPHIC - Delete field 529 - No condition
    [bib.set('529', 'a', 'dummy') for bib in all_records()]
    assert all([bib.get_value('529', 'a') for bib in all_records()])
    [batch_edit.edit_56(bib) for bib in all_records()]
    assert not any([bib.get_value('529', 'a') for bib in defaults])
    assert all([bib.get_value('529', 'a') for bib in speeches + votes])

def test_edit_57():
    # add 999
    [batch_edit.edit_57(bib) for bib in all_records()]
    date = datetime.now().astimezone(timezone('US/Eastern')).strftime(r'%Y%m%d')
    assert all([f'jsb{date}' in bib.get_values('999', 'a') for bib in all_records()])
    assert all([date in bib.get_values('999', 'b') for bib in all_records()])
    assert all([f'b' in bib.get_values('999', 'c') for bib in all_records()])
    
### abstracted functions

@pytest.mark.skip(reason='Not implemented yet')
def test_delete_field():
    pass

@pytest.mark.skip(reason='Not implemented yet')
def test_change_tag():
    pass

@pytest.mark.skip(reason='Not implemented yet')
def test_delete_indicators():
    pass

@pytest.mark.skip(reason='Not implemented yet')
def test_delete_subfield():
    pass