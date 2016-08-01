(function() {
  'use strict';

  angular
    .module('corvus')
    .controller('TaskInfoController', TaskInfoController);

  /* @ngInject */
  function TaskInfoController($stateParams, notify, utils, taskService) {
    var taskInfo = this;

    taskInfo.id = $stateParams.taskId;
    taskInfo.param = '""';
    taskInfo.refresh = activate;

    activate();

    function activate() {
      taskInfo.loading = true;

      taskService.getTask(taskInfo.id)
        .then(function(response) {
          taskInfo.loading = false;

          var res = response.data;
          taskInfo.operation = res.operation;
          taskInfo.createAt = utils.formatDate(res.created_at);
          taskInfo.updateAt = utils.formatDate(res.updated_at);
          taskInfo.statusLabel = taskService.getStatusLabel(res.status);
          taskInfo.statusClass = taskService.getStatusClass(res.status);
          taskInfo.param = JSON.parse(res.param);
          taskInfo.reason = res.reason;
        }, function(err) {
          taskInfo.loading = false;
          notify.warn(err.data.message);
        });
    }
  }
})();
