(function() {
  'use strict';

  angular
    .module('corvus')
    .controller('NodeInfoController', NodeInfoController);

  /* @ngInject */
  function NodeInfoController($stateParams, $mdDialog, notify, nodeService,
                              cmdService) {
    var nodeInfo = this;

    nodeInfo.info = {};
    nodeInfo.popupReshard = nodeService.popupReshard;
    nodeInfo.quitCluster = nodeService.quitCluster;
    nodeInfo.executeCommand = cmdService.popup;

    activate();

    function activate() {
      nodeService.getNode($stateParams.nodeId)
        .then(function(response){
          nodeInfo.info = response.data;
        }, function(err) {
          notify.warn(err.data.message);
        });
    }
  }
})();
