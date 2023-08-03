from config.config import SEIRAL_CONFIG
check_list = []
for m in SEIRAL_CONFIG:
    for key,val in SEIRAL_CONFIG[m].items():
        check_list.append(key) 