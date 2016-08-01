(function() {
  'use strict';

  angular
    .module('corvus')
    .directive('cvClusterAdd', cvClusterAdd);

  /* @ngInject */
  function cvClusterAdd() {
    return {
      controller: ClusterAddController,
      controllerAs: 'clusterAdd',
      restrict: 'EA',
    };
  }

  /* @ngInject */
  function ClusterAddController($mdDialog, $state, utils, clusterService, notify) {
    var clusterAdd = this;

    clusterAdd.nodes = [];
    clusterAdd.cancel = utils.cancel;
    clusterAdd.addCluster = addCluster;
    clusterAdd.input = input;
    clusterAdd.commit = commit;

    function addCluster() {
      $mdDialog.show({
        templateUrl: '/static/template/cluster/add.html',
        controller: ClusterAddController,
        controllerAs: 'clusterAdd',
      });
    }

    function input() {
      clusterAdd.nodes = [];

      if (!clusterAdd.node) {
        return;
      }
      var components = clusterAdd.node.split(':');
      if (components.length != 2 || !components[0] || !components[1]) {
        return;
      }

      clusterAdd.loading = true;
      clusterService.getClusterByHost(components[0], components[1])
        .then(function(response) {
          clusterAdd.loading = false;
          clusterAdd.nodes = response.data.nodes;
        }, function(err) {
          clusterAdd.loading = false;
          notify.warn(err.data.message);
        });
    }

    function commit() {
      if (clusterAdd.nodes.length <= 0) {
        notify.warn('节点数量为 0');
        return;
      }
      if (!clusterAdd.name) {
        notify.warn('集群名为必填');
        return;
      }
      clusterAdd.submitting = true;
      var components = clusterAdd.node.split(':');
      clusterService.addCluster(components[0], components[1],
                                {name: clusterAdd.name})
        .then(function(response) {
          if (response.data.status === 0) {
            utils.cancel();
            $state.go('cluster', {}, {reload: true});
          } else {
            notify.warn('添加失败');
          }
          clusterAdd.submitting = false;
        }, function(err) {
          notify.warn(err.data.message);
          clusterAdd.submitting = false;
        });
    }
  }
})();
