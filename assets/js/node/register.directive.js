(function() {
  'use strict';

  angular
    .module('corvus')
    .directive('cvNodeAdd', cvNodeAdd);

  /* @ngInject */
  function cvNodeAdd() {
    var directive = {
      controller: NodeRegisterController,
      controllerAs: 'nodeReg',
      restrict: 'A',
    };
    return directive;
  }

  /* @ngInject */
  function NodeRegisterController($mdDialog, utils, notify, nodeService) {
    var nodeAdd = this;

    nodeAdd.entries = [{index: 1}];
    nodeAdd.cancel = utils.cancel;
    nodeAdd.commit = commit;
    nodeAdd.registerNodes = registerNodes;

    function commit() {
      var nodes = utils.getAddresses(nodeAdd.entries);
      if (nodes.length <= 0) {
        notify.warn('添加节点后再提交');
        return;
      }

      nodeAdd.submitting = true;
      nodeService.register({nodes: nodes})
        .then(function(response) {
          if (response.data.status == -1) {
            notify.warn(response.data.message);
          } else {
            notify.notice('已成功添加');
            utils.cancel();
          }
          nodeAdd.submitting = false;
        }, function(err) {
          notify.warn(err.data.message);
          nodeAdd.submitting = false;
        });
    }

    function registerNodes() {
      $mdDialog.show({
        templateUrl: '/static/template/node/register.html',
        controller: NodeRegisterController,
        controllerAs: 'nodeReg',
      });
    }
  }
})();
