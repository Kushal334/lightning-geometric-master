import os
import inspect
import os.path as osp
import numpy as np
from functools import partial
from hydra.utils import instantiate
import torch
from torch.utils.data import random_split
from torch_geometric.data import DataLoader
from pytorch_lightning import LightningDataModule
import torch_geometric
from torch_geometric.datasets import PPI
import torch_geometric.transforms as T
from examples.core.base_dataset_samplers import BaseDatasetSamplerMixin
from examples.core.base_tasks_mixin import BaseTasksMixin


def del_attr(kwargs, name):
    try:
        del kwargs[name]
    except:
        pass


class BaseDataset(BaseDatasetSamplerMixin, BaseTasksMixin, LightningDataModule):

    NAME = ...

    def __init__(
        self,
        *args,
        **kwargs,
    ):

        self._threshold = kwargs.get("threshold", None)
        self.__instantiate_transform(kwargs)
        BaseDatasetSamplerMixin.__init__(self, *args, **kwargs)
        BaseTasksMixin.__init__(self, *args, **kwargs)
        self.clean_kwargs(kwargs)
        LightningDataModule.__init__(self, *args, **kwargs)

        self.dataset_train = None
        self.dataset_val = None
        self.dataset_test = None

        self._seed = 42
        self._num_workers = 2
        self._shuffle = True
        self._drop_last = False
        self._pin_memory = True
        self._follow_batch = []

        self._hyper_parameters = {}

    def __handle_mixin(self):
        pass

    def clean_kwargs(self, kwargs):
        LightningDataModuleArgs = inspect.getargspec(LightningDataModule.__init__).args
        keys = list(kwargs.keys())
        for key in keys:
            if key not in LightningDataModuleArgs:
                del_attr(kwargs, key)

    @property
    def config(self):
        return {"dataset_config": {}}

    def __instantiate_transform(self, kwargs):
        self._pre_transform = None
        self._transform = None
        self._train_transform = None
        self._val_transform = None
        self._test_transform = None

        for k in [k for k in kwargs]:
            if "transform" in k and kwargs.get(k) is not None:
                transforms = []
                for t in kwargs.get(k):
                    if t.get("activate") is not None:
                        if t.activate is False:
                            continue
                        del t["activate"]
                    transforms.append(instantiate(t))
                transform = T.Compose(transforms)
                setattr(self, f"_{k}", transform)
                del kwargs[k]

    @property
    def num_features(self):
        pass

    @property
    def num_classes(self):
        pass

    @property
    def hyper_parameters(self):
        return {"num_features": self.num_features, "num_classes": self.num_classes}

    def prepare_data(self):
        pass