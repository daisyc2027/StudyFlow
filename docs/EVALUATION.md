# Synthetic scheduler comparison

Fixed date 2030-01-07. FIFO is capacity/deadline-aware at creation, then does not adapt. 
Priority-weighted minutes sum priority × allocated minutes, not learning outcomes. 
Movement counts existing bookings released/replaced; new bookings are not historical moves.

| Scenario / phase | Violations | Remaining min | Priority × min | Existing moved/released |
|---|---:|---:|---:|---:|
| ample capacity / adaptive_initial | 0 | 0 | 7200 | 0 |
| ample capacity / fifo_initial | 0 | 0 | 7200 | 0 |
| limited capacity favours need / adaptive_initial | 0 | 60 | 5400 | 0 |
| limited capacity favours need / fifo_initial | 0 | 60 | 1800 | 0 |
| FIFO fits urgent work better / adaptive_initial | 0 | 30 | 2100 | 0 |
| FIFO fits urgent work better / fifo_initial | 0 | 0 | 3360 | 0 |

Tiny exhaustive oracle finds 30 more allocatable minutes in “FIFO fits urgent work better”.

| zero availability change / adaptive_initial | 0 | 0 | 5700 | 0 |
| zero availability change / fifo_initial | 0 | 0 | 5700 | 0 |
| zero availability change / adaptive_after_change | 0 | 30 | 3600 | 2 |
| zero availability change / fifo_nonadaptive_after_change | 1 | 0 | 5700 | 0 |
| no capacity / adaptive_initial | 0 | 30 | 0 | 0 |
| no capacity / fifo_initial | 0 | 30 | 0 | 0 |
| pre-existing protected conflict / adaptive_after_change | 1 | 0 | 2400 | 0 |
| pre-existing protected conflict / fifo_nonadaptive_after_change | 1 | 0 | 2400 | 0 |

These six small scenarios illustrate behaviour and limitations; they do not establish universal superiority or educational benefit. Protected conflicts are reported violations, not newly generated overbooking. The FIFO-better deadline case is deliberately retained.
