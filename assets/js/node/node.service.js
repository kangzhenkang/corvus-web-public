(function() {
  'use strict';

  angular
    .module('corvus')
    .service('nodeService', NodeService);

  /* @ngInject */
  function NodeService($http, $mdDialog, notify, clusterService, taskService) {
    this.getNode = getNode;
    this.getNodes = getNodes;
    this.popupReshard = popupReshard;
    this.quitCluster = quitCluster;
    this.add = add;
    this.register = register;
    this.quit = quit;
    this.getCount = getCount;
    this.getMasters = getMasters;
    this.getMastersSample = getMastersSample;
    this.remove = remove;

    function getNode(nodeId) {
      return $http.get('/api/node/' + nodeId);
    }

    function getNodes(page, filters, numResults) {
      var params = {page: page};
      if (filters) {
        params.q = filters;
      }
      if (numResults) {
        params.results_per_page = numResults;
      }
      return $http.get('/api/node', {params: params});
    }

    function getCount(clusterId) {
      return $http.get('/api/node/count/' + clusterId);
    }

    function getMasters(clusterId) {
      return $http.get('/api/node/masters/' + clusterId);
    }

    function getMastersSample(clusterId) {
      return $http.get('/api/node/masters/' + clusterId + '/sample?limit=3');
    }

    function quit(data) {
      return $http.post('/api/node/quit', data);
    }

    function add(data) {
      return $http.post('/api/node/add', data);
    }

    function register(data) {
      return $http.post('/api/node/register', data);
    }

    function remove(nodeId) {
      return $http.delete('/api/node/' + nodeId);
    }

    function popupReshard(node) {
      if (node.role != 'master') {
        return;
      }
      clusterService.popupReshard({
        clusterId: node.clusterId,
        id: node.id,
        host: node.host,
        port: node.port
      });
    }

    function quitCluster(node) {
      var confirm = $mdDialog.confirm().title('退出集群');
      var msg = '节点 ' + node.host + ':' + node.port + ' 是';
      if (node.role == 'master') {
        msg += '主节点，';
        if (node.slots > 0) {
          msg += '有 ' + node.slots + ' 个槽位，';
        }
      } else {
        msg += '从节点，';
      }
      msg += '确定要退出？';
      confirm = confirm.textContent(msg).cancel('取消').ok('确定');

      $mdDialog.show(confirm).then(function() {
        quit({
          clusterId: node.clusterId,
          nodes: [{host: node.host, port: node.port, nodeId: node.nodeId}]
        }).then(function(response) {
          taskService.notifyTask({taskId: response.data.task_id});
        }, function(err) {
          notify.warn(err.data.message);
        });
      });
    }
  }
})();
