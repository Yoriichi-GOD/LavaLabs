from atmospheric_lab.experiment import selection_plan, confirm_selection


def scores(**values):
    return {key:{'mcrmse':value} for key,value in values.items()}


def test_custom_candidate_cannot_win_by_beating_table_but_losing_official():
    plan=selection_plan(scores(table=1.,official=.9,no_fallback=.85,spatial=.86))
    retained,gate=confirm_selection(plan,scores(table=1.,official=.8,no_fallback=.9))
    assert retained=='official'
    assert 'failed' in gate['reasons'][-1]


def test_control_is_not_selected_using_confirmation_and_no_novel_switch():
    plan=selection_plan(scores(table=.8,official=.9,no_fallback=.85,spatial=.86))
    retained,_=confirm_selection(plan,scores(table=.9,official=.7,spatial=.6))
    assert retained=='table' and not plan['challenger_eligible']


def test_novel_must_beat_both_controls_and_degraded_control_reverts():
    plan=selection_plan(scores(table=1.,official=.9,no_fallback=.86,spatial=.85))
    retained,_=confirm_selection(plan,scores(table=.9,official=1.,spatial=.95))
    assert retained=='table'
    retained,_=confirm_selection(plan,scores(table=.9,official=1.,spatial=.8))
    assert retained=='spatial'


def test_numerical_ties_prefer_simpler_and_reject_confirmation_tie():
    plan=selection_plan(scores(table=.9,official=.9-1e-12,no_fallback=.9,spatial=.9))
    assert plan['candidate']=='table'
    plan=selection_plan(scores(table=1.,official=.95,no_fallback=.9,spatial=.9))
    assert plan['candidate']=='no_fallback'
    retained,_=confirm_selection(plan,scores(table=1.,official=.95,no_fallback=.95))
    assert retained=='official'
