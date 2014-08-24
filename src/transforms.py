import abc
from sklearn.decomposition import PCA
import numpy as np
import joblib


class Transform(object):
    def __init__(self, storage):
        self.STORAGE_SUPER_NAME = 'transforms'
        self.FILE_NAMES_EXT = 'mat'
        self.MODEL_NAME_EXT = 'pkl'
        self.storage = storage
        self.super_folder = self.storage.get_super_folder(self.STORAGE_SUPER_NAME)
        self.storage.ensure_dir(self.super_folder)

    @abc.abstractmethod
    def fit(self):
        """ do preperation """

    @abc.abstractmethod
    def transform(self):
        """ transform the data to the new domain """


class PCA_Transform(Transform):
    def __init__(self, storage, n_components=50):
        super(PCA_Transform, self).__init__(storage)
        self.STORAGE_SUB_NAME = 'pca'
        self.STORAGE_MODEL_NAME = 'pca_model'
        self.MODEL_NAME = '%s.%s' % (self.STORAGE_MODEL_NAME, self.MODEL_NAME_EXT)
        self.sub_folder = self.storage.get_sub_folder(self.STORAGE_SUPER_NAME, self.STORAGE_SUB_NAME)
        self.storage.ensure_dir(self.sub_folder)
        self.model_path = self.storage.get_model_path(self.STORAGE_SUPER_NAME, self.MODEL_NAME)
        self._transform = None
        self.n_components = n_components

    def fit(self, data_generator, force=False):
        if force or not self.storage.check_exists(self.model_path):
            print 'calculated'
            self._transform = PCA(n_components=self.n_components)

            def mid_generator():
                for t, des in data_generator:
                    yield des

            X = np.vstack(mid_generator())
            self._transform.fit(X)
            joblib.dump(self._transform, self.model_path)
        else:
            self._transform = joblib.load(self.model_path)

    def transform(self, data_generator, force=False):
        """
        returns a generator.
        """
        for t, des in data_generator:
            instance_name = "%s.%s" % (t['img_id'], self.FILE_NAMES_EXT)
            instance_path = self.storage.get_instance_path(self.STORAGE_SUPER_NAME, self.STORAGE_SUB_NAME, instance_name)

            if force or not self.storage.check_exists(instance_path):
                result = self._transform.transform(des)
                self.storage.save_instance(instance_path, result)
            else:
                result = self.storage.load_instance(instance_path)

            yield t, result
