(function() {
  'use strict';

  angular
    .module('corvus')
    .controller('AgentUpdateAllController', AgentUpdateAllController);

  /* @ngInject */
  function AgentUpdateAllController(utils, notify, agentService, githubApi) {
    var manager = this;

    manager.cancel = utils.cancel;
    manager.submit = submit;

    function submit() {
      if (!manager.newVersion) {
        notify.warn('填写一个版本');
        return;
      }
      if (manager.version && manager.version === manager.newVersion) {
        notify.warn('指定一个新版本再提交');
      }
      agentService.updateAll(manager, manager.newVersion, manager.host,
        function(data) {
          notify.notice('任务已提交');
          utils.cancel();
        });
    }
  }
})();
