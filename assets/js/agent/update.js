(function() {
  'use strict';

  angular
    .module('corvus')
    .controller('AgentUpdateController', AgentUpdateController);

  /* @ngInject */
  function AgentUpdateController(agentService, taskService, notify, utils) {
    var updater = this;

    updater.cancel = utils.cancel;
    updater.submit = submit;

    function submit() {
      if (!updater.newVersion) {
        notify.warn('填写一个版本');
        return;
      }
      var data = {
        host: updater.host,
        port: updater.port,
        newVersion: updater.newVersion
      };
      agentService.update(updater, data, function(data) {
        taskService.notifyTask({taskId: data.task_id});
        utils.cancel();
      });
    }
  }
})();
