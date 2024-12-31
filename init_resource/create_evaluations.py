# create data set for evaludation
from langsmith import Client

from init_resource.eval_data.data_qa import QA_EXAMPLES
inputs = [i['input'] for i in QA_EXAMPLES]
outputs = [i['output'] for i in QA_EXAMPLES]

client = Client()
list(client.list_datasets())
EVALSET_NAME = "home_assistant_recommendations"

dataset = client.create_dataset(EVALSET_NAME)
# client.create_examples(inputs=inputs, outputs=outputs, dataset_id=dataset.id)


client.read_dataset(dataset_id='538bbb14-19fd-48de-8966-43dc3c92ec0b')
client.read_dataset(EVALSET_NAME=EVALSET_NAME)