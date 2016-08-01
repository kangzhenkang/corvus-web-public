(function() {
  'use strict';

  angular
    .module('corvus')
    .controller('ClusterNodeController', ClusterNodeController);

  /* @ngInject */
  function ClusterNodeController($mdDialog, $mdToast, notify, utils, nodeService, taskService) {
    var clusterNode = this;

    clusterNode.entries = [{index: 1, isSlave: true}];
    clusterNode.addNodes = addNodes;
    clusterNode.deleteEntry = deleteEntry;
    clusterNode.addEntry = addEntry;
    clusterNode.cancel = utils.cancel;
    clusterNode.masterNodes = [];

    activate();

    function activate() {
      nodeService.getMasters(clusterNode.clusterId)
        .then(function(response) {
          clusterNode.masterNodes = response.data.nodes;
        }, function(err) {
          notify.warn(err.data.message);
        });
    }

    function addEntry(isSlave) {
      clusterNode.entries.unshift({isSlave: isSlave});
    }

    function deleteEntry(entry) {
      utils.remove(clusterNode.entries, entry);
    }

    function addNodes() {
      if (clusterNode.masterNodes.length <= 0) {
        return;
      }

      var data = {
        clusterId: clusterNode.clusterId,
        nodes: [],
        current: clusterNode.masterNodes[0],
      };

      var checked = [];

      for (var i = 0; i < clusterNode.entries.length; i++) {
        var v = clusterNode.entries[i];
        if (!v.host || !v.port || (v.isSlave && !v.master)) {
          continue;
        }
        var nodes = utils.getAddresses([v]);
        var role = v.isSlave ? 'slave' : 'master';

        for (var j = 0; j < nodes.length; j++) {
          var n = nodes[j];
          var addr = n.host + ':' + n.port;
          if (checked.indexOf(addr) !== -1) {
            notify.warn('主机端口有重复 ' + addr);
            return;
          }
          checked.push(addr);
          var node = {addr: n.host + ':' + n.port, role: role};
          if (v.isSlave) {
            node.master = v.master;
          }
          data.nodes.push(node);
        }
      }

      if (data.nodes.length <= 0) {
        notify.warn("没有可添加的节点");
        return;
      }

      clusterNode.submitting = true;
      nodeService.add(data)
        .then(function(response) {
          if (response.data.status == -1) {
            notify.warn(response.data.message);
          } else {
            utils.cancel();
            taskService.notifyTask({taskId: response.data.task_id});
          }
          clusterNode.submitting = false;
        }, function(err) {
          notify.warn(err.data.message);
          clusterNode.submitting = false;
        });
    }
  }
})();
