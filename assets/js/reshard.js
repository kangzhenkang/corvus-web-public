(function() {
  'use strict';

  angular
    .module('corvus')
    .controller('ReshardController', ReshardController);

  /* @ngInject */
  function ReshardController($mdDialog, $mdToast, utils, notify, clusterService, taskService,
                            nodeService) {
    var reshard = this;

    reshard.nodes = [];
    reshard.cancel = utils.cancel;
    reshard.currentNode = {host: reshard.host, port: reshard.port};
    reshard.slotsCount = slotsCount;
    reshard.currentNodeSlotsCount = currentNodeSlotsCount;
    reshard.divide = divide;
    reshard.resharding = resharding;
    reshard.page = reshard.pages = 1;
    reshard.loadMore = loadMore;

    activate();

    function activate() {
      reshard.loadingNodes = true;

      nodeService.getNodes(reshard.page, {
        filters: [{
          name: 'cluster_id',
          op: '==',
          val: reshard.clusterId
        }]
      }).then(function(response) {
        reshard.page = response.data.page;
        reshard.pages = response.data.total_pages;

        angular.forEach(response.data.objects, function(v) {
          if (v.role === 'master') {
            v.reshardSlots = 0;
            if (v.id === reshard.id) {
              reshard.currentNode = v;
            } else {
              reshard.nodes.push(v);
            }
          }
        reshard.loadingNodes = false;
        });
      }, function(err) {
        reshard.loadingNodes = false;
        notify.warn(err.data.message);
      });
    }

    function loadMore() {
      if (reshard.page >= reshard.pages) {
        return;
      }
      reshard.page++;
      activate();
    }

    function slotsCount(node) {
      return Number(node.reshardSlots || 0) + node.slots;
    }

    function currentNodeSlotsCount() {
      var resharded = 0;
      angular.forEach(reshard.nodes, function(v, k) {
        resharded += Number(v.reshardSlots || 0);
      });
      return reshard.currentNode.slots - resharded;
    }

    function divide() {
      var count = reshard.nodes.length;
      if (count <= 0) {
        return;
      }

      var i = 0;
      var avg = parseInt(reshard.currentNode.slots / count);
      var remain = reshard.currentNode.slots - count * avg;
      for (i = 0; i < count; i++) {
        reshard.nodes[i].reshardSlots = avg;
      }

      for (i = 0; i < count; i++) {
        if (remain <= 0) {
          break;
        }
        reshard.nodes[i].reshardSlots += 1;
        remain -= 1;
      }
    }

    function resharding() {
      var data = {plan: [], clusterId: reshard.clusterId};
      var total = 0;
      angular.forEach(reshard.nodes, function(v) {
        if (v.reshardSlots > 0) {
          total += v.reshardSlots;
          data.plan.push({
            dst: {host: v.host, port: v.port},
            src: {host: reshard.currentNode.host, port: reshard.currentNode.port},
            count: v.reshardSlots,
          });
        }
      });
      if (data.plan.length <= 0 || total > reshard.currentNode.slots) {
        notify.warn('没有可迁移的槽位');
        return;
      }

      clusterService.reshard(data)
        .then(function(response) {
          taskService.notifyTask({taskId: response.data.task_id});
          utils.cancel();
        }, function(err) {
          notify.warn(err.data.message);
        });
    }
  }
})();
