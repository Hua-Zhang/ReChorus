# -*- coding: UTF-8 -*-

import torch

from models.BPR import BPR


class NCF(BPR):
    @staticmethod
    def parse_model_args(parser, model_name='NCF'):
        parser.add_argument('--layers', type=str, default='[64]',
                            help="Size of each layer.")
        return BPR.parse_model_args(parser, model_name)

    def __init__(self, args, corpus):
        self.layers = eval(args.layers)
        self.dropout = args.dropout
        BPR.__init__(self, args, corpus)

    def _define_params(self):
        self.mf_u_embeddings = torch.nn.Embedding(self.user_num, self.emb_size)
        self.mf_i_embeddings = torch.nn.Embedding(self.item_num, self.emb_size)
        self.mlp_u_embeddings = torch.nn.Embedding(self.user_num, self.emb_size)
        self.mlp_i_embeddings = torch.nn.Embedding(self.item_num, self.emb_size)
        self.embeddings = ['mf_u_embeddings', 'mf_i_embeddings', 'mlp_u_embeddings', 'mlp_i_embeddings']

        self.mlp = torch.nn.ModuleList([])
        pre_size = 2 * self.emb_size
        for i, layer_size in enumerate(self.layers):
            self.mlp.append(torch.nn.Linear(pre_size, layer_size))
            pre_size = layer_size
        self.dropout_layer = torch.nn.Dropout(p=self.dropout)
        self.prediction = torch.nn.Linear(pre_size + self.emb_size, 1, bias=False)

    def forward(self, feed_dict):
        self.check_list, self.embedding_l2 = [], []
        u_ids = feed_dict['user_id']  # [batch_size]
        i_ids = feed_dict['item_id']  # [batch_size, -1]

        u_ids = u_ids.unsqueeze(-1).repeat((1, i_ids.shape[1]))  # [batch_size, -1]

        mf_u_vectors = self.mf_u_embeddings(u_ids)
        mf_i_vectors = self.mf_i_embeddings(i_ids)
        mlp_u_vectors = self.mlp_u_embeddings(u_ids)
        mlp_i_vectors = self.mlp_i_embeddings(i_ids)
        self.embedding_l2.extend([mf_u_vectors, mf_i_vectors, mlp_u_vectors, mlp_i_vectors])

        mf_vector = mf_u_vectors * mf_i_vectors
        mlp_vector = torch.cat([mlp_u_vectors, mlp_i_vectors], dim=-1)
        for layer in self.mlp:
            mlp_vector = layer(mlp_vector).relu()
            mlp_vector = self.dropout_layer(mlp_vector)

        output_vector = torch.cat([mf_vector, mlp_vector], dim=-1)
        prediction = self.prediction(output_vector)

        out_dict = {'prediction': prediction.view(feed_dict['batch_size'], -1), 'check': self.check_list}
        return out_dict
