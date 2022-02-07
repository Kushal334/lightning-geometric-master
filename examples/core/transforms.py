from typing import List, Optional
import torch
from torch_geometric.utils import normalized_cut
from torch_geometric.data import Data, Batch

class AddFeatsByKeys(object):
    """This transform takes a list of attributes names and if allowed, add them to x
    Example:
        Before calling "AddFeatsByKeys", if data.x was empty
        - transform: AddFeatsByKeys
          params:
              list_add_to_x: [False, True, True]
              feat_names: ['normal', 'rgb', "elevation"]
              input_nc_feats: [3, 3, 1]
        After calling "AddFeatsByKeys", data.x contains "rgb" and "elevation". Its shape[-1] == 4 (rgb:3 + elevation:1)
        If input_nc_feats was [4, 4, 1], it would raise an exception as rgb dimension is only 3.
    Paremeters
    ----------
    list_add_to_x: List[bool]
        For each boolean within list_add_to_x, control if the associated feature is going to be concatenated to x
    feat_names: List[str]
        The list of features within data to be added to x
    input_nc_feats: List[int], optional
        If provided, evaluate the dimension of the associated feature shape[-1] found using feat_names and this provided value. It allows to make sure feature dimension didn't change
    stricts: List[bool], optional
        Recommended to be set to list of True. If True, it will raise an Exception if feat isn't found or dimension doesn t match.
    delete_feats: List[bool], optional
        Wether we want to delete the feature from the data object. List length must match teh number of features added.
    """

    def __init__(
        self,
        list_add_to_x: List[bool],
        feat_names: List[str],
        input_nc_feats: List[Optional[int]] = None,
        stricts: List[bool] = None,
        delete_feats: List[bool] = None,
    ):

        self._feat_names = feat_names
        self._list_add_to_x = list_add_to_x
        self._delete_feats = delete_feats
        if self._delete_feats:
            assert len(self._delete_feats) == len(self._feat_names)
        from torch_geometric.transforms import Compose

        num_names = len(feat_names)
        if num_names == 0:
            raise Exception("Expected to have at least one feat_names")

        assert len(list_add_to_x) == num_names

        if input_nc_feats:
            assert len(input_nc_feats) == num_names
        else:
            input_nc_feats = [None for _ in range(num_names)]

        if stricts:
            assert len(stricts) == num_names
        else:
            stricts = [True for _ in range(num_names)]

        transforms = [
            AddFeatByKey(add_to_x, feat_name, input_nc_feat=input_nc_feat, strict=strict)
            for add_to_x, feat_name, input_nc_feat, strict in zip(list_add_to_x, feat_names, input_nc_feats, stricts)
        ]

        self.transform = Compose(transforms)

    def __call__(self, data):
        data = self.transform(data)
        if self._delete_feats:
            for feat_name, delete_feat in zip(self._feat_names, self._delete_feats):
                if delete_feat:
                    delattr(data, feat_name)
        return data

    def __repr__(self):
        msg = ""
        for f, a in zip(self._feat_names, self._list_add_to_x):
            msg += "{}={}, ".format(f, a)
        return "{}({})".format(self.__class__.__name__, msg[:-2])


class AddFeatByKey(object):
    """This transform is responsible to get an attribute under feat_name and add it to x if add_to_x is True
    Paremeters
    ----------
    add_to_x: bool
        Control if the feature is going to be added/concatenated to x
    feat_name: str
        The feature to be found within data to be added/concatenated to x
    input_nc_feat: int, optional
        If provided, check if feature last dimension maches provided value.
    strict: bool, optional
        Recommended to be set to True. If False, it won't break if feat isn't found or dimension doesn t match. (default: ``True``)
    """

    def __init__(self, add_to_x, feat_name, input_nc_feat=None, strict=True):

        self._add_to_x: bool = add_to_x
        self._feat_name: str = feat_name
        self._input_nc_feat = input_nc_feat
        self._strict: bool = strict

    def __call__(self, data: Data):
        if not self._add_to_x:
            return data
        feat = getattr(data, self._feat_name, None)
        if feat is None:
            if self._strict:
                raise Exception("Data should contain the attribute {}".format(self._feat_name))
            else:
                return data
        else:
            if self._input_nc_feat:
                feat_dim = 1 if feat.dim() == 1 else feat.shape[-1]
                if self._input_nc_feat != feat_dim and self._strict:
                    raise Exception("The shape of feat: {} doesn t match {}".format(feat.shape, self._input_nc_feat))
            x = getattr(data, "x", None)
            if x is None:
                if self._strict and data.pos.shape[0] != feat.shape[0]:
                    raise Exception("We expected to have an attribute x")
                if feat.dim() == 1:
                    feat = feat.unsqueeze(-1)
                data.x = feat
            else:
                if x.shape[0] == feat.shape[0]:
                    if x.dim() == 1:
                        x = x.unsqueeze(-1)
                    if feat.dim() == 1:
                        feat = feat.unsqueeze(-1)
                    data.x = torch.cat([x, feat], dim=-1)
                else:
                    raise Exception(
                        "The tensor x and {} can't be concatenated, x: {}, feat: {}".format(
                            self._feat_name, x.pos.shape[0], feat.pos.shape[0]
                        )
                    )
        return data

    def __repr__(self):
        return "{}(add_to_x: {}, feat_name: {}, strict: {})".format(
            self.__class__.__name__, self._add_to_x, self._feat_name, self._strict
        )

def normalized_cut_2d(edge_index, pos):
    row, col = edge_index
    edge_attr = torch.norm(pos[row] - pos[col], p=2, dim=1)
    return normalized_cut(edge_index, edge_attr, num_nodes=pos.size(0))