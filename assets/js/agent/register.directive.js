(function() {
  'use strict';

  angular
    .module('corvus')
    .directive('cvAgentRegister', cvAgentRegister);

  /* @ngInject */
  function cvAgentRegister() {
    return {
      controller: AgentRegisterController,
      controllerAs: 'agentRegister',
      restrict: 'AE',
    };
  }

  /* @ngInject */
  function AgentRegisterController($mdDialog, utils, notify, agentService) {
    var agentRegister = this;

    agentRegister.entries = [{index: 1}];
    agentRegister.cancel = utils.cancel;
    agentRegister.commit = commit;

    agentRegister.register = register;

    function register() {
      $mdDialog.show({
        templateUrl: '/static/template/agent/agent.html',
        controller: AgentRegisterController,
        controllerAs: 'agentRegister',
      });
    }

    function commit() {
      var nodes = [];
      angular.forEach(agentRegister.entries, function(v) {
        if (v.host && v.port) {
          nodes.push({host: v.host, port: v.port});
        }
      });
      if (nodes.length <= 0) {
        notify.warn('没有可添加的节点');
        return;
      }

      agentRegister.submitting = true;
      agentService.add({agents: nodes})
        .then(function(response) {
          if (response.data.status == -1) {
            notify.warn(response.data.message);
          } else {
            notify.notice('已成功添加');
            utils.cancel();
          }
          agentRegister.submitting = false;
        }, function(err) {
          notify.warn(err.data.message);
          agentRegister.submitting = false;
        });
    }
  }
})();
