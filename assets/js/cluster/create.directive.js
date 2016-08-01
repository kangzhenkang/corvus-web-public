(function() {
  'use strict';

  angular
    .module('corvus')
    .directive('cvClusterNew', cvClusterNew);

  /* @ngInject */
  function cvClusterNew() {
    return {
      controller: ClusterNewController,
      controllerAs: 'clusterNew',
      restrict: 'A',
    };
  }

  /* @ngInject */
  function ClusterNewController($mdDialog, $mdToast, notify, utils, clusterService, taskService) {
    var clusterNew = this;

    clusterNew.nodeEntries = [{index: 1}];
    clusterNew.cancel = utils.cancel;
    clusterNew.createCluster = createCluster;
    clusterNew.addNode = addNode;
    clusterNew.deleteEntry = deleteEntry;
    clusterNew.commit = commit;

    clusterNew.slaves = 1;
    clusterNew.description = '';

    function createCluster() {
      $mdDialog.show({
        templateUrl: '/static/template/cluster/create.html',
        controller: ClusterNewController,
        controllerAs: 'clusterNew',
      });
    }

    function addNode() {
      var length = clusterNew.nodeEntries.length;
      clusterNew.nodeEntries.unshift({index: length});
    }

    function deleteEntry(entry) {
      utils.remove(clusterNew.nodeEntries, entry);
    }

    function commit() {
      var nodes = utils.getAddresses(clusterNew.nodeEntries);
      if (nodes.length <= 0) {
        notify.warn('添加节点后再提交');
        return;
      }

      if (!clusterNew.name || !/^[0-9a-zA-Z_-]+$/.test(clusterNew.name)) {
        notify.warn('集群名称 "' + (clusterNew.name || '') + '" 不符合规范');
        return;
      }

      var maxSlaves = parseInt(nodes.length / 3 - 1);
      maxSlaves = maxSlaves < 0 ? 0 : maxSlaves;
      if (maxSlaves < Number(clusterNew.slaves || 0)) {
        notify.warn('最大从节点数为 ' + maxSlaves);
        return;
      }

      clusterNew.submitting = true;

      clusterService.createCluster({
        name: clusterNew.name,
        description: clusterNew.description,
        slaves: Number(clusterNew.slaves || 0),
        nodes: nodes
      }).then(function(response) {
        if (response.data.status == -1) {
          notify.warn(response.data.message);
        } else {
          utils.cancel();
          taskService.notifyTask({taskId: response.data.task_id});
        }
        clusterNew.submitting = false;
      }, function(err) {
        notify.warn(err.data.message);
        clusterNew.submitting = false;
      });
    }
  }
})();
