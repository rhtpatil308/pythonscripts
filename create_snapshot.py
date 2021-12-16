"""
@title: create-snapshots.py
@description: Create snapshot of given servers list.
"""
# standard modules import
import json, sys, os, argparse, logging
from datetime import datetime
from xml.etree.ElementTree import dump
from colorlog import ColoredFormatter
from pyVim.task import WaitForTask
from pyVim import connect
import csv

try:
    from pyVmomi import vim
    from pyVim.connect import SmartConnectNoSSL
except ImportError:
    from pyVim.connect import SmartConnectNoSSL


class SnapshotManager(object):
    log = logging.getLogger(__name__)
    ch = logging.StreamHandler()
    formatter = ColoredFormatter(
        '%(log_color)s %(levelname)-8s [%(filename)s:%(lineno)d - %(funcName)10s()] %(message)s ', '%c')
    ch.setFormatter(formatter)
    log.addHandler(ch)
    log.setLevel(logging.DEBUG)
    log.propagate = False

    @classmethod
    def get_all_vm_snapshots(cls, vm):
        results = []
        try:
            rootSnapshots = vm.snapshot.rootSnapshotList
        except:
            rootSnapshots = []
        for snapshot in rootSnapshots:
            results.append(snapshot)
            results += cls.get_child_snapshots(snapshot)
        return results

    @classmethod
    def get_child_snapshots(cls, snapshot):
        results = []
        snapshots = snapshot.childSnapshotList
        for snapshot in snapshots:
            results.append(snapshot)
            results += cls.get_child_snapshots(snapshot)
        return results

    @classmethod
    def get_obj(cls, content, vimtype, name):
        """
         Get the vsphere object associated with a given text name
        """
        obj = None
        container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
        for c in container.view:
            if c.name == name:
                obj = c
                break
        return obj

    @classmethod
    def create_snapshot(cls, vs_host, vs_user, vs_pass):
        try:
            cls.log.debug("connecting to vcenter . . .")
            v_server = connect.ConnectNoSSL(host=vs_host, user=vs_user,
                                            pwd=vs_pass, port=443)
            content = v_server.RetrieveContent()
            get_version = content.about
            cls.log.info(f"[+] successfully connected to version {get_version.fullName}")

            cls.log.debug("[+] reading server list . . .")
            server_cfg = os.path.join(sys.path[0], 'servers.ini')
            with open(server_cfg) as fd:
                # servers = fd.read().splitlines()
                server = csv.reader(fd)
                for row in server:
                    vm_name = row[0]
                    cl_name = row[1]
            objview = content.viewManager.CreateContainerView(content.rootFolder, [vim.Datacenter], True)
            dcList = objview.view
            objview.Destroy()
            for dc in dcList:
                for cl in dc.hostFolder.childEntity:
                    if cl.name == cl_name:
                        for host in cl.host:
                            for vm in host.vm:
                                if vm.name == vm_name:
                                    cls.log.info("Found virtual machine %s" %vm_name)
                                    vm_obj = cls.get_obj(content, [vim.VirtualMachine], vm_name)
                                    cls.log.info("------ CREATING SNAPSHOT OF VM ------")
                                    cls.log.info(f"Creating snapshot of {vm_name}")
                                    snapshot_name = vm_name + "-" + str(datetime.now())
                                    description = f"This {snapshot_name} is taken by {vs_user}, " \
                                                  f"Before removing this snapshot " \
                                                  f"contact with {vs_user}"
                                    dump_memory = False
                                    quiesce = False
                                    cls.log.debug("Snapshot creation process started, please wait until complete...")
                                    WaitForTask(vm_obj.CreateSnapshot(snapshot_name, description, dump_memory, quiesce))
                                    cls.log.debug("Snapshot created successfully")
                                    cls.log.info("------ SNAPSHOT DETAILS ------")
                                    snapshots = cls.get_all_vm_snapshots(vm_name)
                                    if len(snapshots) > 0:
                                        for snapshot in snapshots:
                                            cls.log.debug(f"SNAPSHOT NAME : {snapshot.name}")
                                            cls.log.info("------ ------ ------ ------")
            cls.log.info("------ DONE ------")
        except Exception as ex:
            cls.log.error(ex)


snapshotMangerObj = SnapshotManager()
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--vs_host", type=str, required=True, help="please enter vs_host")
    parser.add_argument("--vs_user", type=str, required=True, help="please enter username")
    parser.add_argument("--vs_password", type=str, required=True, help="please enter password")
    args = parser.parse_args()
    snapshotMangerObj.create_snapshot(args.vs_host, args.vs_user, args.vs_password)

    pass