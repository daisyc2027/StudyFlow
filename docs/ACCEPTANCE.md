# Acceptance-to-test map

All fixtures are synthetic. HTTP tests exercise real Flask routes and SQLite. Browser tests launch the actual app and use the real scheduler/evidence/database; there are no mocked core paths. `python scripts/check.py --all` runs lint, all non-browser tests, reproducible evaluation and Chromium. Add `--webkit` for a separately labelled WebKit run. Pytest “deselected” counts are complementary marker groups, not skips.

| Case | Exact tests (under tests/) |
|---|---|
| A01 Accounts/isolation/CSRF | test_auth.py::test_accounts_health_csrf; test_auth_validation.py; test_inputs.py::test_owned_links_and_database_integrity; test_evidence_priority.py::test_starting_report_and_owner; test_adaptation.py::test_deadline_repair_overdue_and_owner; test_experience.py::test_pdf_owner_private_and_prefilled_context; test_adversarial.py::test_csrf_all_mutations_leave_records_unchanged, test_add_practice_foreign_id_isolation; test_browser.py::test_browser_auth |
| A02 Inputs/restart/validation | test_inputs.py::test_inputs_restart_edit_archive, test_invalid_availability_atomic, test_bad_dates_budgets_and_preserved_form, test_owned_links_and_database_integrity; test_browser.py::test_browser_inputs, test_browser_edit_evidence_attachment_lock_move_archive |
| A03 Evidence | test_evidence_priority.py::test_independent_recency_unknown_and_corrections, test_stored_evidence_retry_correction, test_marks_do_not_rate_free_text_or_overall_grade, test_starting_report_and_owner; test_adaptation.py::test_pause_timing_refresh_duplicate_complete_no_rating, test_miss_skip_replacement_no_debt, test_completion_outcome_once |
| A04 Priority | test_evidence_priority.py::test_priority_exact_deadlines_waiting, test_priority_bounds_monotonic; test_scheduler.py::test_demand_deadline_ties_and_spacing; test_adaptation.py::test_late_completion_waiting_uses_local_actual_date |
| A05 Scheduling | test_scheduler.py::test_capacity_block_examples, test_demand_deadline_ties_and_spacing, test_generated_plan_invariants, test_generation_stable_ids_and_unplaced; test_browser.py::test_browser_saved_plan |
| A06 Adaptation | test_adaptation.py::test_miss_skip_replacement_no_debt, test_capacity_change_locks_active_and_budget, test_reconcile_next_day_preserves_unfinished, test_bounded_displacement_and_no_space, test_evidence_rebalances_and_rollback, test_deadline_repair_overdue_and_owner, test_past_missed_high_need_displaces_future_lower_need; test_adversarial.py::test_random_repair_conservation_and_immutability, test_random_database_repair_sequences |
| A07 Lifecycle | test_adaptation.py::test_pause_timing_refresh_duplicate_complete_no_rating, test_completion_outcome_once, test_reconcile_next_day_preserves_unfinished; test_adversarial.py::test_concurrent_double_completion; test_browser.py::test_full_feedback_plan_practice_repair |
| A08 Full fresh browser workflow | test_browser.py::test_full_feedback_plan_practice_repair (two subjects, feedback, three targets, exams/capacity, plan, start/pause/resume/finish/outcome, Progress, missed-work repair, override, reload/logout/login) |
| A09 Frontend | test_browser.py::test_main_screens_mobile_empty_and_links, test_browser_edit_evidence_attachment_lock_move_archive, test_full_feedback_plan_practice_repair; screenshots in docs/evidence |
| A10 Optional reference PDFs | test_experience.py::test_pdf_owner_private_and_prefilled_context, test_invalid_upload_no_record, test_oversize_request, test_attachment_rollback_cleanup; test_browser.py::test_browser_edit_evidence_attachment_lock_move_archive; full core browser workflow has no attachment and requests only localhost |
| A11 Failure/recovery | test_adaptation.py::test_evidence_rebalances_and_rollback and protected/expired tests; test_adversarial.py::test_concurrent_double_completion, test_stale_settings_csrf_and_archive_retry; test_inputs.py::test_inputs_restart_edit_archive; test_migrations.py::test_upgrade_preserves_existing_user_initial_evidence_and_checks |
| A12 Fresh setup/handover | test_migrations.py::test_fresh_migrations_manual_workflow_seed_and_restart, test_upgrade_preserves_existing_user_initial_evidence_and_checks; scripts/fresh_setup.py (also in --all) executes normal shell migration/run/seed/check commands; clean environment verified and HANDOFF.md written |

Fixed randomized seeds/settings: 20300107 / 150 priority examples; 4042030 / 120 generation examples; 7072030 / 200 repair cases; 7172030 / 25 real-database sequences of up to six changes. Deadline checks disabled only for Hypothesis timing thresholds, not scheduling deadlines; assertions remain mandatory. Failing generated cases would be retained by Hypothesis and converted to explicit regressions.

Independent evaluation: scripts/benchmark.py is test-only; test_adversarial.py::test_tiny_oracle_and_independent_checker and test_additional_tiny_oracle_fixtures independently check legal placements. See EVALUATION.md and evidence/scheduler-comparison.json. The FIFO-better case and pre-existing protected conflict are preserved.

## Review extension acceptance

All original A01–A12 cases remain required. The additional mapping is:

| Requirement | Test evidence |
|---|---|
| Pure transitions, daily replay, timezone/cap | test_review_algorithm.py; test_every_transition_and_corrected_backdated_replay |
| Off by default, uniqueness, enable/disable, separate credit | test_enable_existing_outcome_uniqueness_correction_and_separate_credit; test_no_data_disabling_ownership_and_rollback |
| Populated old-schema upgrade, no implicit recurring work | test_review_upgrade_retains_populated_base_and_defaults_off; original fresh migration tests |
| Shared allocator, balancing, due/deadline/horizon | test_shared_balancing_not_before_and_deadline; test_mixed_invariants; test_due_update_locked_conflict_and_future_horizon |
| Miss replacement, protected disable and unchanged IDs | test_actual_review_reservations_miss_disable_and_stability; test_same_date_locked_due_change_conflict |
| Route auth/CSRF/stale/retry, no data/capacity | test_review_routes_no_data_capacity_late_outcome_disable; test_review_routes_owner_csrf_and_stale |
| Unrated completion, late/corrected outcomes, daily repeats | test_unrated_review_late_outcome_correction_daily_replay; test_later_rated_practice_resumes_after_unrated_review_at_equal_timestamp |
| Actual completion local date | test_actual_completion_timezone_not_scheduled_or_submission_date |
| Active/paused disable, expiry and archive | test_due_change_protects_active_paused_locked_and_deadline; test_teacher_general_evidence_not_completed_review_and_archive |
| Atomic failure and concurrent outcomes/tasks | test_review_evidence_schedule_transaction_rolls_back; test_review_concurrent_completion_exact_retry |
| Foreign session/source/task links | test_composite_review_links_and_late_session_ownership |
| Seeded real DB sequences | test_seeded_real_database_mutation_invariants (12 isolated scenarios × 8 daily changes) |
| Real UI/mobile opt-in/no capacity/disable | test_browser_review_opt_in_no_data_outcome_no_capacity_disable |
| Complete fresh dated review loop + persistence | test_browser_complete_dated_review_loop (both engines) |
| Normal production-clock setup + review enable/late outcome | scripts/fresh_setup.py via scripts/check.py --all |
