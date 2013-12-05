#!/usr/bin/python
import sys, struct
import re
import Segment
import InodeMap

from threading import Thread, Lock, Condition, Semaphore
from Segment import SegmentManagerClass
from Disk import DiskClass
from Inode import Inode, getmaxinode, setmaxinode
from InodeMap import InodeMapClass
from FileDescriptor import FileDescriptor
from DirectoryDescriptor import DirectoryDescriptor
from Constants import FILENAMELEN
from FSE import FileSystemException
import Disk

DEBUG = True

def find_parent_name(path):
    parent, sep, element = path.rpartition("/")
    if parent == '':
        parent = '/'
    return parent

def find_filename(path):
    parent, sep, element = path.rpartition("/")
    return element

#takes an absolute path, iterates through the components in the name
def get_path_components(path):
    for component in path[1:].strip().split("/"):
        yield component

class LFSClass:
    def __init__(self, initdisk=True):
        pass

    # open an existing file or directory
    def open(self, path, isdir=False):
        print "Inside LFS.open for path :",path
        inodenumber = self._searchfiledir(path)
        print "Inside LFS.open, HERE1", inodenumber
        if inodenumber is None:
            raise FileSystemException("Path Does Not Exist")
        # create and return a Descriptor of the right kind
        if isdir:
            return DirectoryDescriptor(inodenumber)
        else:
            return FileDescriptor(inodenumber)

    def create(self, filename, isdir=False):
        print "Inside LFSClass:create for filename :", filename
        fileinodenumber = self._searchfiledir(filename)
        print "Inside LFSClass:create 1.", fileinodenumber
        if fileinodenumber is not None:
            raise FileSystemException("File Already Exists")

        # create an Inode for the file
        # Inode constructor writes the inode to disk and implicitly updates the inode map
        newinode = Inode(isdirectory=isdir)

        # now append the <filename, inode> entry to the parent directory
        parentdirname = find_parent_name(filename)
        parentdirinodenumber = self._searchfiledir(parentdirname)
        if parentdirinodenumber is None:
            raise FileSystemException("Parent Directory Does Not Exist")
        parentdirblockloc = InodeMap.inodemap.lookup(parentdirinodenumber)
        parentdirinode = Inode(str=Segment.segmentmanager.blockread(parentdirblockloc))
        self.append_directory_entry(parentdirinode, find_filename(filename), newinode)

        if isdir:
            return DirectoryDescriptor(newinode.id)
        else:
            return FileDescriptor(newinode.id)

    # return metadata about the given file
    def stat(self, pathname):
        inodenumber = self._searchfiledir(pathname)
        if inodenumber is None:
            raise FileSystemException("File or Directory Does Not Exist")

        inodeblocknumber = InodeMap.inodemap.lookup(inodenumber)
        inodeobject = Inode(str=Segment.segmentmanager.blockread(inodeblocknumber))
        return inodeobject.filesize, inodeobject.isDirectory

    # delete the given file
    def unlink(self, pathname):
        # XXX - do this tomorrow! after the meteor shower!
        pass

    # write all in memory data structures to disk
    def sync(self):
        if DEBUG:
            print "Inide LFS.sync"
        # XXX - do this tomorrow! after the meteor shower!
        inode = Inode()
        inodeblockid = InodeMap.inodemap.lookup(inode.id)
        str, gencount = InodeMap.inodemap.save_inode_map(Inode.getmaxinode())
        inode.write(0,str)
        Segment.segmentmanager.currentseg.superblock.inodemapgeneration = gencount
        Segment.segmentmanager.currentseg.superblock.inodemaplocation = inodeblockid
        Segment.segmentmanager.flush()
        


    # restore in memory data structures (e.g. inode map) from disk
    def restore(self):
        imlocation = Segment.segmentmanager.locate_latest_inodemap()
        print repr(imlocation) #SEE
        str=Disk.disk.blockread(imlocation)
        print repr(str)#SEE
        iminode = Inode(str)
        imdata = iminode.read(0, 10000000)
        # restore the latest inodemap from wherever it may be on disk
        setmaxinode(InodeMap.inodemap.restore_inode_map(imdata))

    # for a given file or directory named by path,
    # return its inode number if the file or directory exists,
    # else return None
    # Writing this assuming the path would be canonicalized wrt root
    def _searchfiledir(self, path):
        # XXX - do this tomorrow! after the meteor shower! -Ok bro:)
        print "Inside LFSClass.searchfiledir : for path :", path
        if path[0]!= '/':
            print "Inside LFSClass.searchfiledir : Path not canonicalized properly"
            return None
        #print InodeMap.inodemap.mapping
        
        inode = 1
        path = path[1:] # removing the first /
        pattern = "([\w|\d|_|\-|\.]*)/*(.*)"
        while len(path)>0:
            result = re.match(pattern, path, flags=re.IGNORECASE)
            if result:
                l = result.groups()
                inode =  self._search_file_dir(inode, l[0])
                if inode == -1:
                    return None
                path = l[1]
            else:
                raise FileSystemException("Inside LFSClass.searchfiledir : Malformed file name passed " + str(path))
        return inode

    def _search_file_dir(self, inodenumber, tosearch):
        print "Inside LFSClass._searchfiledir for inode and file/dir" , inodenumber, tosearch
        if len(tosearch) == 0:
            raise FileSystemException("Inside LFSClass._searchfiledir : Bad file name passed " + str(tosearch))
        
        directory = DirectoryDescriptor(inodenumber)
        for name, inode in directory.enumerate():
            if name == tosearch:
                return inode        

        return -1
            



    # add the new directory entry to the data blocks,
    # write the modified inode to the disk,
    # and update the inode map
    def append_directory_entry(self, dirinode, filename, newinode):
        dirinode.write(dirinode.filesize, struct.pack("%dsI" % FILENAMELEN, filename, newinode.id))

filesystem = None
