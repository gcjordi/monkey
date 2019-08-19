import json
from common.data.zero_trust_consts import *
from monkey_island.cc.models.zero_trust.finding import Finding


class ZeroTrustService(object):
    @staticmethod
    def get_pillars_grades():
        pillars_grades = []
        for pillar in PILLARS:
            pillars_grades.append(ZeroTrustService.__get_pillar_grade(pillar))
        return pillars_grades

    @staticmethod
    def __get_pillar_grade(pillar):
        all_findings = Finding.objects()
        pillar_grade = {
            "pillar": pillar,
            STATUS_CONCLUSIVE: 0,
            STATUS_INCONCLUSIVE: 0,
            STATUS_POSITIVE: 0,
            STATUS_UNEXECUTED: 0
        }

        tests_of_this_pillar = PILLARS_TO_TESTS[pillar]

        test_unexecuted = {}
        for test in tests_of_this_pillar:
            test_unexecuted[test] = True

        for finding in all_findings:
            test_unexecuted[finding.test] = False
            test_info = TESTS_MAP[finding.test]
            if pillar in test_info[PILLARS_KEY]:
                pillar_grade[finding.status] += 1

        pillar_grade[STATUS_UNEXECUTED] = sum(1 for condition in test_unexecuted.values() if condition)

        return pillar_grade

    @staticmethod
    def get_directives_status():
        all_directive_statuses = {}

        # init with empty lists
        for pillar in PILLARS:
            all_directive_statuses[pillar] = []

        for directive, directive_tests in DIRECTIVES_TO_TESTS.items():
            for pillar in DIRECTIVES_TO_PILLARS[directive]:
                all_directive_statuses[pillar].append(
                    {
                        "directive": DIRECTIVES[directive],
                        "tests": ZeroTrustService.__get_tests_status(directive_tests),
                        "status": ZeroTrustService.__get_directive_status(directive_tests)
                    }
                )

        return all_directive_statuses

    @staticmethod
    def __get_directive_status(directive_tests):
        worst_status = STATUS_UNEXECUTED
        all_statuses = set()
        for test in directive_tests:
            all_statuses |= set(Finding.objects(test=test).distinct("status"))

        for status in all_statuses:
            if ORDERED_TEST_STATUSES.index(status) < ORDERED_TEST_STATUSES.index(worst_status):
                worst_status = status

        return worst_status

    @staticmethod
    def __get_tests_status(directive_tests):
        results = []
        for test in directive_tests:
            test_findings = Finding.objects(test=test)
            results.append(
                {
                    "test": TESTS_MAP[test][TEST_EXPLANATION_KEY],
                    "status": ZeroTrustService.__get_lcd_worst_status_for_test(test_findings)
                }
            )
        return results

    @staticmethod
    def __get_lcd_worst_status_for_test(all_findings_for_test):
        current_status = STATUS_UNEXECUTED
        for finding in all_findings_for_test:
            if ORDERED_TEST_STATUSES.index(finding.status) < ORDERED_TEST_STATUSES.index(current_status):
                current_status = finding.status

        return current_status

    @staticmethod
    def get_all_findings():
        all_findings = Finding.objects()
        enriched_findings = [ZeroTrustService.__get_enriched_finding(f) for f in all_findings]
        return enriched_findings

    @staticmethod
    def __get_enriched_finding(finding):
        test_info = TESTS_MAP[finding.test]
        enriched_finding = {
            # TODO add test explanation per status.
            "test": test_info[FINDING_EXPLANATION_BY_STATUS_KEY][finding.status],
            "pillars": test_info[PILLARS_KEY],
            "status": finding.status,
            "events": ZeroTrustService.__get_events_as_dict(finding.events)
        }
        return enriched_finding

    @staticmethod
    def __get_events_as_dict(events):
        return [json.loads(event.to_json()) for event in events]

    @staticmethod
    def get_statuses_to_pillars():
        results = {
            STATUS_CONCLUSIVE: [],
            STATUS_INCONCLUSIVE: [],
            STATUS_POSITIVE: [],
            STATUS_UNEXECUTED: []
        }
        for pillar in PILLARS:
            results[ZeroTrustService.__get_status_for_pillar(pillar)].append(pillar)

        return results

    @staticmethod
    def get_pillars_to_statuses():
        results = {}
        for pillar in PILLARS:
            results[pillar] = ZeroTrustService.__get_status_for_pillar(pillar)

        return results

    @staticmethod
    def __get_status_for_pillar(pillar):
        grade = ZeroTrustService.__get_pillar_grade(pillar)
        for status in ORDERED_TEST_STATUSES:
            if grade[status] > 0:
                return status
        return STATUS_UNEXECUTED
