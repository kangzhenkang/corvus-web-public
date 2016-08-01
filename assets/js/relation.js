(function() {
  'use strict';

  angular
    .module('corvus')
    .controller('RelationController', RelationController);

  /* @ngInject */
  function RelationController($mdDialog, utils, notify, clusterService) {
    var relation = this;

    relation.items = [];
    relation.close = utils.cancel;
    relation.updateNodes = updateNodes;

    activate();

    function updateNodes() {
      relation.updateNodes = true;
      clusterService.updateNodeList(relation.clusterId, relation.items)
        .then(function(response) {
          relation.updateNodes = false;
          if (response.data.status == -1) {
            notify.warn(response.data.message);
          } else {
            relation.reload();
            utils.cancel();
          }
        }, function(err) {
          relation.updateNodes = false;
          notify.warn(err.data.message);
        });
    }

    function activate() {
      relation.loadingNodes = true;
      clusterService.getRelation(relation.clusterId)
        .then(function(response) {
          relation.loadingNodes = false;
          if (response.data.status == -1) {
            notify.warn(response.data.message);
          } else {
            relation.items = response.data.nodes;
          }
        }, function(err) {
          relation.loadingNodes = false;
          notify.warn(err.data.message);
        });
    }
  }
})();
