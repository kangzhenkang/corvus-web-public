(function() {
  'use strict';

  angular
    .module('corvus')
    .controller('CommandController', CommandController);

  /* @ngInject */
  function CommandController($mdDialog, utils, cmdService, notify) {
    var cmd = this;

    cmd.cancel = utils.cancel;
    cmd.executeCommand = executeCommand;
    cmd.messages = [];

    function executeCommand() {
      if (!cmd.command || !cmd.host || !cmd.port) {
        return;
      }
      cmd.loading = true;
      cmdService.executeCommand(cmd.host, cmd.port, cmd.command)
        .then(function(response) {
          if (response.data.status == -1) {
            notify.warn(err.data.message);
          } else {
            cmd.messages.unshift({
              cmd: cmd.command,
              result: response.data.result
            });
            cmd.command = '';
          }
          cmd.loading = false;
        }, function(err) {
          notify.warn(err.data.message);
          cmd.loading = false;
        });
    }
  }
})();
