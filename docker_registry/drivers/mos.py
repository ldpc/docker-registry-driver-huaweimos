# -*- coding: utf-8 -*-
"""
docker_registry.drivers.mos
~~~~~~~~~~~~~~~~~~~~~~~~~~
mos is Open Storage Service provided by huawei.com
see detail http://www.hwclouds.com/
"""
import os
import logging

from com.hws.s3.client.huawei_s3 import HuaweiS3
from com.hws.s3.models.s3object import S3Object

from docker_registry.core import driver
from docker_registry.core import exceptions
from docker_registry.core import lru

logging.basicConfig(filename = os.path.join(os.getcwd(), '/var/log/mos/log.txt'), level = logging.WARN, filemode = 'w', format = '%(asctime)s - %(levelname)s: %(message)s')  


class Storage(driver.Base):
    def __init__(self, path=None, config=None):
        self.access_key_id = config.mos_accessid
        self.secret_access_key = config.mos_accesskey
        self.is_secure = config.secure or False
        self.server = config.mos_host or "s3-hd1.hwclouds.com"
        self.bucket = config.mos_bucket
        self.mos = self.make_connection()
        self._root_path = config.storage_path or '/'
        if not self._root_path.endswith('/'):
            self._root_path += '/'
        logging.debug("AK=%s,SK=%s,secure=%s,bucker=%s,root_path=%s" %
                     (self.access_key_id, self.secret_access_key, self.is_secure,
                     self.server, self._root_path))

    def make_connection(self):
        if self.server:
            hw_mos = HuaweiS3(self.access_key_id,
                                   self.secret_access_key,
                                   self.is_secure,
                                   self.server)
        else:
            hw_mos = HuaweiS3(self.access_key_id,
                                   self.secret_access_key,
                                   self.is_secure)
        return hw_mos

    def _init_path(self, path=None):
        path = self._root_path + path if path else self._root_path
        if path:
            if path.startswith('/'):
                path = path[1:]
            if path.endswith('/'):
                path = path[:-1]
        return path

    @lru.get
    def get_content(self, path):
        path = self._init_path(path)
        if not self.exists(path):
            raise exceptions.FileNotFoundError("File not found %s" % path)
        return self.get_store(path)


    def get_store(self, path, buffer_size=None):
        obj = self.mos.get_object(self.bucket, path)
        if obj:
            data = str(obj.object[0])
        return data

    @lru.set
    def put_content(self, path, content):
        """Method to put content."""
        path = self._init_path(path)
        logging.debug("path=%s,type(content)=%s"%(path,type(content)))
        self.put_store(path, content)
        return path

    def put_store(self, path, content, buff_size=None):
        try:
            with open("/tmp/content","w+") as fp:
                fp.write(content)
            s3b = S3Object("/tmp/content")
            self.mos.create_object(self.bucket, path, s3b)
        except Exception:
             raise IOError("Could not put path: %s.content=%s" % (path, content))

    def stream_read(self, path, bytes_range=None):
        """Method to stream read."""
        pass
    
    def stream_write(self, path, fp):
        """Method to stream write."""
        pass

    def list_directory(self, path=None):
        """Method to list directory."""
        path = self._init_path(path)
        list_obj = self.mos.list_objects(self.bucket, path)
        if list_obj:
            for key in list_obj.keyslist:
                 yield key

    @lru.get
    def exists(self, path):
        """Method to test exists."""
        logging.debug("Check exist os path=%s" % path)
        for i in range(1, 3):
            try:
                return self.mos.check_object_exist(self.bucket, path)
            except Exception:
                continue
        logging.debug("Path=%s doesn't exist")
        return False

    @lru.remove
    def remove(self, path):
        """Method to remove."""
        path = self._init_path(path)
        try:
            self.mos.delete_object(self.bucket, path, None)
        except Exception:
            raise(exceptions.ConnectionError("Communication with mos fail"))

    def get_size(self, path):
        """Method to get the size."""
        path = self._init_path(path)
        logging.debug("Get file size of %s" % path)
        try:
            file_size = self.mos.get_object_filesize(self.bucket, path)
            if file_size is not None:
                logging.debug("Size of %s is %s" % (path, file_size))
                return file_size
            else:
                raise exceptions.FileNotFoundError("Unable to get size of %s" % path)
        except Exception:
            raise(exceptions.ConnectionError("Unable to get size of %s" % path))

