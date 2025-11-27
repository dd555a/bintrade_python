from Data import data_append_auto, fix_data
from Stats import stats_append_all
data_append_auto()
stats_append_all()
fix_data() #fix data duplicates which may happen due to daylight saving time
