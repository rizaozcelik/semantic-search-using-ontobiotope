import json

from src.ontobiotope import OntoBiotope
from src.utils import extract_mention_node_matchings, matching_to_embedding
from src.mention_set import MentionSet
from src.projection_model import ProjectionModel
from src.finder import Finder

import numpy as np
#%%


def train(configs, pretrained_word_embeddings):
    ontobiotope = OntoBiotope(ontobiotope_path=configs['ontobiotope_raw'])
    ontobiotope.initialize()
    ontobiotope.save_graph(configs['ontobiotope_nx'])

    ontobiotope.enrich_with_cooccurence(configs['train'])
    ontobiotope.save_graph(configs['ontobiotope_enriched'])

    node_embeddings = ontobiotope.learn_embeddings()
    OntoBiotope.save_embeddings(node_embeddings, configs['node_embeddings'])

    mention_files = [configs['train'], configs['dev']]
    mention_set = MentionSet(mention_files)
    mention_embeddings = mention_set.learn_embeddings(pretrained_word_embeddings)
    MentionSet.save_embeddings(mention_embeddings, configs['mention_embeddings_100'])

    train_matchings = extract_mention_node_matchings(configs['train'])
    X_train, Y_train = matching_to_embedding(train_matchings, mention_embeddings, node_embeddings)
    model = ProjectionModel()
    model.train(X_train, Y_train)
    model.save(configs['model_path'])


def test(configs):
    ontobiotope = OntoBiotope(configs['ontobiotope_raw'])
    ontobiotope.load_graph(configs['ontobiotope_enriched'])
    node_embeddings = OntoBiotope.load_embeddings(configs['node_embeddings'])
    mention_embeddings = MentionSet.load_embeddings(configs['mention_embeddings_100'])

    model = ProjectionModel()
    model.load(configs['model_path'])
    test_matchings = extract_mention_node_matchings(configs['dev'])
    X_test, _ = matching_to_embedding(test_matchings, mention_embeddings, node_embeddings)
    Y_test = [node_id for mention, node_id in test_matchings]
    preds = model.predict(X_test, node_embeddings)
    model.evaluate(Y_test, preds, ontobiotope.graph)


with open('configs.json') as f:
    configs = json.load(f)

print('Loading pretrained word vectors...')
with open(configs['word_embeddings_100']) as embedding_file:
    pretrained_word_embeddings = json.load(embedding_file)

#%%
train(configs, pretrained_word_embeddings)
test(configs)

model = ProjectionModel()
model.load(configs['model_path'])
ontobiotope = OntoBiotope(configs['ontobiotope_raw'])
ontobiotope.load_graph(configs['ontobiotope_nx'])
node_embeddings = OntoBiotope.load_embeddings(configs['node_embeddings'])

finder = Finder()
finder.construct_inverted_index(configs['train'])
#%%
max_distance = 2
query = 'children with age less than 5'
query_embedding = MentionSet.mention_to_embedding(query, pretrained_word_embeddings)
predicted_node_id = model.predict(np.array(query_embedding).reshape((1, 100)), node_embeddings)[0]
#%%
search_results = finder.find_related_docs(ontobiotope.graph, predicted_node_id, max_distance)
#%%
results = finder.display_search_results(search_results, configs['train'])
