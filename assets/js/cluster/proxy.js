(function() {
  'use strict';

  angular
    .module('corvus')
    .controller('ClusterProxyController', ClusterProxyController);

  /* @ngInject */
  function ClusterProxyController($state, $mdDialog, utils, notify,
                                  clusterService, proxyService, taskService,
                                  githubApi, nodeService) {
    var clusterProxy = this;

    clusterProxy.entries = [{index: 1}];
    clusterProxy.cancel = utils.cancel;
    clusterProxy.commit = commit;
    clusterProxy.deleteEntry = deleteEntry;
    clusterProxy.addEntry = addEntry;

    clusterProxy.action = 'create';
    clusterProxy.config = {
      thread: 4,
      client_timeout: 600,
      server_timeout: 0,
      statsd: 'statsd:8125',
    };

    clusterProxy.config.node = "获取中...";
    nodeService.getMastersSample(clusterProxy.clusterId).then(function(response){
      var masters = response.data.nodes;
      if (masters.length) {
        clusterProxy.config.node = masters.map(
          function(m){return m.host + ':' + m.port}
          ).join(',');
      }
    });

    githubApi.getRelease(function(release) {
      clusterProxy.config.version = release;
    });

    function create() {
      proxyService.create(clusterProxy, function(data) {
        utils.cancel();
        taskService.notifyTask({taskId: data.task_id});
        clusterProxy.reload();
      });
    }

    function add() {
      proxyService.add(clusterProxy.entries, clusterProxy, function() {
        utils.cancel();
        clusterProxy.reload();
      });
    }

    function commit() {
      switch (clusterProxy.action) {
        case 'create':
          create();
          break;
        case 'add':
          add();
          break;
      }
    }

    function deleteEntry(entry) {
      utils.remove(clusterProxy.entries, entry);
    }

    function addEntry() {
      var length = clusterProxy.entries.length;
      clusterProxy.entries.unshift({index: length});
    }
  }
})();
