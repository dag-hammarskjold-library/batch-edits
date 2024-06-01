import sys, random
from dlx.marc import Bib, Auth, BibSet, AuthSet, Query, Condition
from batch_edits.scripts import batch_edit

defaults = [Bib() for i in range(0, 10)]
speeches = [Bib().set('989', 'a', 'Speeches') for i in range(0, 10)]
votes = [Bib().set('989', 'a', 'Voting Data') for i in range(0, 10)]
def all_records(): return defaults + speeches + votes

def test_script_runs(bibs):
    batch_edit.run(connect='mongomock://localhost')

def test_edit_1():
    # 1. BIBLIOGRAPHIC - Delete field 099 if subfield c = internet
    [bib.set('099', 'c', 'internet') for bib in all_records()]
    assert all([bib.get_value('099', 'c') == 'internet' for bib in defaults])
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
    assert all([bib.get_value('029', 'a') == 'other' for bib in speeches + votes])

def test_edit_3():
    # 3. BIBLIOGRAPHIC, SPEECHES, VOTING - Delete field 930 - If NOT 930:UND* OR 930:UNGREY* OR 930:CIF* OR 930:DIG* OR 930:HUR*  oR 930:PER*
    # ?subfield $a?
    values = ['UND', 'UNGREY', 'CIF', 'DIG', 'HUR', 'PER']
    [bib.set('930', 'a', random.choice(values)) for bib in all_records()[:20]]
    [bib.set('930', 'a', 'other') for bib in all_records()[20:]]
    assert len([bib for bib in all_records() if bib.get_value('930', 'a') == 'other']) == 10
    [batch_edit.edit_3(bib) for bib in all_records()]
    assert len([bib for bib in all_records() if bib.get_value('930', 'a') == 'other']) == 0

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
    assert not any([bib.get_value('008') for bib in defaults])
    assert all([bib.get_value('008') for bib in votes + speeches])

def test_edit_6():
    # 6. BIBLIOGRAPHIC, VOTING - Delete field 035 - IF 089__b is NOT B22 (keep 035 for speeches)
    [bib.set('035', 'a', 'dummy') for bib in all_records()]
    assert all([bib.get_value('035', 'a') for bib in all_records()])
    [batch_edit.edit_6(bib) for bib in all_records()]
    assert not any([bib.get_value('035', 'a') for bib in defaults + votes])
    assert all([bib.get_value('035', 'a') for bib in speeches])

def test_edit_7():
    # 7. BIBLIOGRAPHIC - Delete field 069 - No condition
    [bib.set('069', 'a', 'dummy') for bib in all_records()]
    assert all([bib.get_value('069', 'a') for bib in all_records()])
    [batch_edit.edit_7(bib) for bib in all_records()]
    assert not any([bib.get_value('069', 'a') for bib in defaults])
    assert all([bib.get_value('069', 'a') for bib in speeches + votes])

def test_edit_8():
    # 8. BIBLIOGRAPHIC - Transfer field 100 - to 700
    Auth().set('100', 'a', 'dummy').commit()
    [bib.set('100', 'a', 'dummy') for bib in all_records()]
    assert all([bib.get_value('100', 'a') for bib in all_records()])
    [batch_edit.edit_8(bib) for bib in all_records()]
    assert not any([bib.get_value('100', 'a') for bib in defaults])
    assert all([bib.get_value('700', 'a') for bib in defaults])
    assert all([bib.get_value('100', 'a') for bib in speeches + votes])

def test_edit_9():
    # 9. BIBLIOGRAPHIC - Transfer field 110 - to 710
    Auth().set('110', 'a', 'dummy').commit()
    [bib.set('110', 'a', 'dummy') for bib in all_records()]
    assert all([bib.get_value('110', 'a') for bib in all_records()])
    [batch_edit.edit_9(bib) for bib in all_records()]
    assert not any([bib.get_value('110', 'a') for bib in defaults])
    assert all([bib.get_value('710', 'a') for bib in defaults])
    assert all([bib.get_value('110', 'a') for bib in speeches + votes])

def test_edit_10():
    # 10. BIBLIOGRAPHIC - Transfer field 111 - to 711
    Auth().set('111', 'a', 'dummy').commit()
    [bib.set('111', 'a', 'dummy') for bib in all_records()]
    assert all([bib.get_value('111', 'a') for bib in all_records()])
    [batch_edit.edit_10(bib) for bib in all_records()]
    assert not any([bib.get_value('111', 'a') for bib in defaults])
    assert all([bib.get_value('711', 'a') for bib in defaults])
    assert all([bib.get_value('111', 'a') for bib in speeches + votes])

def test_edit_11():
    # 11. BIBLIOGRAPHIC - Transfer field 130 - to 730
    Auth().set('130', 'a', 'dummy').commit()
    [bib.set('130', 'a', 'dummy') for bib in all_records()]
    assert all([bib.get_value('130', 'a') for bib in all_records()])
    [batch_edit.edit_11(bib) for bib in all_records()]
    assert not any([bib.get_value('130', 'a') for bib in defaults])
    assert all([bib.get_value('730', 'a') for bib in defaults])
    assert all([bib.get_value('130', 'a') for bib in speeches + votes])

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

def test_edit_14():
    # 14. BIBLIOGRAPHIC - Transfer field 440 - To 830
    Auth().set('140', 'a', 'dummy').commit()
    [bib.set('440', 'a', 'dummy') for bib in all_records()]
    assert all([bib.get_value('440', 'a') for bib in all_records()])
    [batch_edit.edit_14(bib) for bib in all_records()]
    assert not any([bib.get_value('440', 'a') for bib in defaults])
    assert all([bib.get_value('830', 'a') == 'dummy' for bib in defaults])
    assert all([bib.get_value('440', 'a') for bib in speeches + votes])

def test_edit_15():
    # 15. BIBLIOGRAPHIC - Transfer field 490 $x - Transfer to 022 $a if the field with the same value does not exists
    [bib.set('490', 'x', 'dummy') for bib in all_records()]
    [bib.set('022', 'a', 'dummy') for bib in defaults[:5]]
    [bib.set('022', 'a', 'other') for bib in defaults[5:]]
    assert len([bib for bib in all_records() if bib.get_value('490', 'x')]) == 30
    assert len([bib for bib in defaults if bib.get_value('022', 'a') == 'dummy']) == 5
    [batch_edit.edit_15(bib) for bib in all_records()]
    assert len([bib for bib in all_records() if bib.get_value('490', 'x')]) == 25
    assert len([bib for bib in defaults if bib.get_value('022', 'a')]) == 10
    assert len([bib for bib in defaults if bib.get_value('022', 'a') == 'other']) == 5
    assert len([bib for bib in speeches + votes if bib.get_value('022', 'a')]) == 0

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
    assert all([bib.get_value('773', 'a') for bib in speeches + votes])

def test_edit_18():
    # 18. BIBLIOGRAPHIC - Delete field 910 - No conditions
    [bib.set('910', 'a', 'dummy') for bib in all_records()]
    assert all([bib.get_value('910', 'a') for bib in all_records()])
    [batch_edit.edit_18(bib) for bib in all_records()]
    assert not any([bib.get_value('910', 'a') for bib in defaults])
    assert all([bib.get_value('910', 'a') for bib in speeches + votes])

    