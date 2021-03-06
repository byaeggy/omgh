import os
import abc
from pascal_utils import VOC2006AnnotationParser, all_classes
import numpy as np
import settings
import cv2
import utils
from parts import CUBParts
from itertools import ifilter


class Dataset(object):

    def __init__(self, base_path):
        self.base_path = base_path

    @abc.abstractmethod
    def get_train(self):
        """ return a generator object that yields dictionares """

    @abc.abstractmethod
    def get_test(self):
        """ return a generator object that yields dictionares """


class CUB_200_2011(Dataset):
    NAME = 'CUB_200_2011'
    IMAGES_FOLDER_NAME = 'images'
    SEGMENTAIONS_FOLDER_NAME = 'segmentations'
    IMAGES_FOLDER_NAME_CROPPED = 'images_cropped'
    IMAGES_FILE_NAME = 'images.txt'
    TRAIN_TEST_SPLIT_FILE_NAME = 'train_test_split.txt'
    CLASS_LABEL_FILE_NAME = 'image_class_labels.txt'
    BBOX_FILE_NAME = 'bounding_boxes.txt'
    PARTS_FOLDER_NAME = 'parts'
    PARTS_FILE_NAME = 'parts.txt'
    PART_LOCS_FILE_NAME = 'part_locs.txt'
    SPLIT_FILE_TRAIN_INDICATOR = '1'
    SPLIT_FILE_TEST_INDICATOR = '0'

    def __init__(self, base_path, images_folder_name=None, full=False):
        super(CUB_200_2011, self).__init__(base_path)
        if full:
            self.full_length = settings.FULL_LENGTH
        if images_folder_name:
            self.IMAGES_FOLDER_NAME = images_folder_name

        self.images_folder = os.path.join(
            self.base_path, self.IMAGES_FOLDER_NAME)
        self.images_folder_cropped = os.path.join(
            self.base_path, self.IMAGES_FOLDER_NAME_CROPPED)
        self.segmentation_mask_folder = os.path.join(
            self.base_path, '..', '..', self.SEGMENTAIONS_FOLDER_NAME)
        self.images_file = os.path.join(
            self.base_path, self.IMAGES_FILE_NAME)
        self.train_test_split_file = os.path.join(
            self.base_path, self.TRAIN_TEST_SPLIT_FILE_NAME)
        self.class_label_file = os.path.join(
            self.base_path, self.CLASS_LABEL_FILE_NAME)
        self.bbox_file = os.path.join(
            self.base_path, self.BBOX_FILE_NAME)
        self.parts_file = os.path.join(
            self.base_path, self.PARTS_FOLDER_NAME, self.PARTS_FILE_NAME)
        self.part_locs_file = os.path.join(
            self.base_path, self.PARTS_FOLDER_NAME, self.PART_LOCS_FILE_NAME)
        self.full = full

    def get_all_images(self, cropped=False):
        with open(self.images_file, 'r') as images_file:
            for line in images_file:
                parts = line.split()
                assert len(parts) == 2
                folder = self.images_folder
                if cropped:
                    folder = self.images_folder_cropped
                yield {'img_id': parts[0],
                       'img_file': os.path.join(folder, parts[1]),
                       'img_file_rel': parts[1]}

    def get_all_segmentations(self):
        for img_info in self.get_all_images():
            yield {'seg_file': os.path.join(self.segmentation_mask_folder, img_info['img_file_rel'][:-3] + 'png'),
                   'img_id': img_info['img_id']}

    def get_segmentation_info(self, img_id):
        """
        don't call this function alot!
        """
        all_of_them = [i for i in ifilter(lambda i: int(i['img_id']) == int(img_id), self.get_all_segmentations())]

        return all_of_them[0]['seg_file']

    def get_all_segmentation_infos(self):
        all_infos = list(self.get_all_segmentations())
        the_hash = {}

        for info in all_infos:
            the_hash[int(info['img_id'])] = info['seg_file']

        return the_hash

    def get_image_info(self, img_id):
        """
        don't call this function alot!
        """
        all_of_them = [i for i in ifilter(lambda i: int(i['img_id']) == int(img_id), self.get_all_images())]

        return all_of_them[0]['img_file']

    def get_all_image_infos(self, relative=False):
        all_infos = list(self.get_all_images())
        the_hash = {}

        info_key = 'img_file'
        if relative:
            info_key = 'img_file_rel'

        for info in all_infos:
            the_hash[int(info['img_id'])] = info[info_key]

        return the_hash

    def gen_cropped_images(self):
        bbox = self.get_bbox()
        with open(self.images_file, 'r') as images_file:
            for line in images_file:
                parts = line.split()
                image_file_address = os.path.join(self.images_folder, parts[1])
                image_file_address_cropped = os.path.join(self.images_folder_cropped, parts[1])
                image_cropped_dir = os.path.dirname(image_file_address_cropped)
                utils.ensure_dir(image_cropped_dir)
                image_id = parts[0]
                image = cv2.imread(image_file_address)
                x, y, w, h = bbox[int(image_id) - 1]
                image = image[y:y+h, x:x+w]
                cv2.imwrite(image_file_address_cropped, image)
                print image_id

    def get_train_test(self, read_extractor, read_extractor_nofull=None, xDim=4096):
        if self.full:
            assert read_extractor_nofull is not None
        trains = []
        tests = []
        indicators = []
        with open(self.train_test_split_file, 'r') as split_file:
            for line in split_file:
                parts = line.split()
                assert len(parts) == 2
                img_id = parts[0]
                indicator = parts[1]
                indicators.append(indicator)
                if indicator == self.SPLIT_FILE_TRAIN_INDICATOR:
                    trains.append(img_id)
                elif indicator == self.SPLIT_FILE_TEST_INDICATOR:
                    tests.append(img_id)
                else:
                    raise Exception("Unknown indicator, %s" % indicator)

        len_trains = len(trains)
        len_tests = len(tests)

        if self.full:
            Xtrain = np.zeros((len_trains * 10, xDim), dtype=np.float32)
            ytrain = np.zeros(len_trains * 10, dtype=np.int)
            Xtest = np.zeros((len_tests * 10, xDim), dtype=np.float32)
            ytest = np.zeros(len_tests * 10, dtype=np.int)
        else:
            Xtrain = np.zeros((len_trains, xDim), dtype=np.float32)
            ytrain = np.zeros(len_trains, dtype=np.int)
            Xtest = np.zeros((len_tests, xDim), dtype=np.float32)
            ytest = np.zeros(len_tests, dtype=np.int)

        with open(self.class_label_file, 'r') as class_label:
            line_num = 0
            train_num = 0
            test_num = 0
            for line in class_label:
                parts = line.split()
                assert len(parts) == 2
                img_id = parts[0]
                img_cls = int(parts[1])
                indicator = indicators[line_num]
                if indicator == self.SPLIT_FILE_TRAIN_INDICATOR:
                    # training
                    if self.full:
                        Xtrain[10 * train_num: 10 * (train_num + 1), :] = read_extractor(img_id)
                        ytrain[10 * train_num: 10 * (train_num + 1)] = np.tile(img_cls, self.full_length)
                    else:
                        Xtrain[train_num, :] = read_extractor(img_id)
                        ytrain[train_num] = img_cls
                    train_num += 1
                else:
                    # testing
                    if self.full:
                        Xtest[test_num, :] = read_extractor_nofull(img_id)
                    else:
                        Xtest[test_num, :] = read_extractor(img_id)
                    ytest[test_num] = img_cls
                    test_num += 1

                line_num += 1

        return Xtrain, ytrain, Xtest, ytest

    def get_train_test_id(self):
        trains = []
        tests = []
        indicators = []
        with open(self.train_test_split_file, 'r') as split_file:
            for line in split_file:
                parts = line.split()
                assert len(parts) == 2
                img_id = parts[0]
                indicator = parts[1]
                indicators.append(indicator)
                if indicator == self.SPLIT_FILE_TRAIN_INDICATOR:
                    trains.append(img_id)
                elif indicator == self.SPLIT_FILE_TEST_INDICATOR:
                    tests.append(img_id)
                else:
                    raise Exception("Unknown indicator, %s" % indicator)

        len_trains = len(trains)
        len_tests = len(tests)
        IDtrain = np.zeros(len_trains, dtype=np.int)
        IDtest = np.zeros(len_tests, dtype=np.int)

        with open(self.class_label_file, 'r') as class_label:
            line_num = 0
            train_num = 0
            test_num = 0
            for line in class_label:
                parts = line.split()
                assert len(parts) == 2
                img_id = parts[0]
                indicator = indicators[line_num]
                if indicator == self.SPLIT_FILE_TRAIN_INDICATOR:
                    # training
                    IDtrain[train_num] = img_id
                    train_num += 1
                else:
                    # testing
                    IDtest[test_num] = img_id
                    test_num += 1

                line_num += 1

        return IDtrain, IDtest

    def get_bbox(self):
        bbox = np.genfromtxt(self.bbox_file, delimiter=' ')
        bbox = bbox[:, 1:]
        return bbox

    def get_parts(self):
        ploc = np.genfromtxt(self.part_locs_file, delimiter=' ').astype(np.int)

        return CUBParts(ploc, self.get_bbox())

    def get_class_dict(self):
        class_dict = {}
        with open(self.class_label_file, 'r') as class_label:
            for line in class_label:
                parts = line.split()
                assert len(parts) == 2
                img_id = parts[0]
                img_cls = int(parts[1])
                class_dict[img_id] = img_cls

        return class_dict


# Bofore using this class make sure that you have first issued the following commands
# python src/scripts/make_segmented_dataset.py
# with approperiat arguments and options.
class CUB_200_2011_Segmented(CUB_200_2011):
    IMAGES_FOLDER_NAME = 'images_segmented'
    IMAGES_FOLDER_NAME_CROPPED = 'images_segmented_cropped'


class CUB_200_2011_Parts_Head(CUB_200_2011):
    IMAGES_FOLDER_NAME = 'images_head'


class CUB_200_2011_Parts_Head_RF(CUB_200_2011):
    IMAGES_FOLDER_NAME = 'images_head_rf'


class CUB_200_2011_Parts_Body(CUB_200_2011):
    IMAGES_FOLDER_NAME = 'images_body'


class CUB_200_2011_Parts_Head_Gray(CUB_200_2011):
    IMAGES_FOLDER_NAME = 'images_gray_head'


class PASCAL_VOC_2006(Dataset):
    NAME = 'PASCAL_VOC_2006'
    ANNOTATIONS_FOLDER_NAME = 'Annotations'
    SETS_FOLDER_NAME = 'ImageSets'
    IMAGES_FOLDER_NAME = 'PNGImages'
    CLASSES = ['bicycle', 'bus', 'car', 'motorbike',
               'cat', 'cow', 'dog', 'horse', 'sheep', 'person']
    SETS_FILE_EXT = 'txt'
    ANNOTATIONS_FILE_EXT = 'txt'
    IMAGE_FILE_EXT = 'png'
    SETS_NAME = ['train', 'test', 'val', 'trainval']
    POSITIVE = '1'
    DIFFICULT = '0'
    NEGATIVE = '-1'

    def __init__(self, base_path):
        super(PASCAL_VOC_2006, self).__init__(base_path)
        self.annotations = os.path.join(
            self.base_path, self.ANNOTATIONS_FOLDER_NAME)
        self.sets = os.path.join(self.base_path, self.SETS_FOLDER_NAME)
        self.images = os.path.join(self.base_path, self.IMAGES_FOLDER_NAME)

    def classes(self):
        return self.CLASSES

    def get_train(self):
        return self.get_set('trainval', object_class=None,
                            difficult=True, trunc=True)

    def get_test(self):
        return self.get_set('test', object_class=None,
                            difficult=True, trunc=True)

    def get_set(self, kind, object_class=None, difficult=False, trunc=True):
        """
        This function returns a generator object.
        `kind` must be one of: ['train', 'test', 'val', 'trainval']
        """
        assert kind in self.SETS_NAME
        if object_class is not None:
            assert object_class in self.CLASSES
            set_file_name = "%s_%s.%s" % (
                object_class, kind, self.SETS_FILE_EXT)
        else:
            set_file_name = "%s.%s" % (kind, self.SETS_FILE_EXT)

        set_file_path = os.path.join(self.sets, set_file_name)

        return self._parse_set(set_file_path, difficult, trunc)

    def _parse_set(self, set_file_path, difficult, trunc):
        with open(set_file_path) as set_file:
            for line in set_file:
                parts = line.split()
                if len(parts) > 1:
                    image_id = parts[0]
                    is_here = True if parts[1] == self.POSITIVE or parts[
                        1] == self.DIFFICULT else False
                else:
                    image_id = parts[0]
                    is_here = True

                if is_here:
                    image_annotations_file = os.path.join(
                        self.annotations, "%s.%s" %
                        (image_id, self.ANNOTATIONS_FILE_EXT))
                    image_file = os.path.join(
                        self.images, "%s.%s" % (image_id, self.IMAGE_FILE_EXT))
                    with open(image_annotations_file, 'r') as content_file:
                        image_annotations_file_content = content_file.read()

                    annon_parser = VOC2006AnnotationParser(
                        image_annotations_file_content)
                    objects = annon_parser.get_objects()

                    if len(objects) == 0:
                        continue

                    all_classes_in_image = all_classes(objects)

                    yield {'img_id': image_id, 'img_file': image_file,
                           'classes': all_classes_in_image, 'objects': objects}
