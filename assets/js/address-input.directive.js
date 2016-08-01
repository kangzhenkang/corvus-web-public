(function() {
  'use strict';

  angular
    .module('corvus')
    .directive('cvAddressInput', cvAddressInput);

  /* @ngInject */
  function cvAddressInput(utils) {
    var directive = {
      templateUrl: '/static/template/address-input.html',
      link: link,
      scope: {
        subheader: '@',
        portHint: '@',
        cvModel: '='
      }
    };
    return directive;

    function link(scope, element, attrs) {
      var m = scope.cvModel;

      scope.portHint = scope.portHint || '如: 8889,8890,8000-8003';

      scope.addEntry = addEntry;
      scope.deleteEntry = deleteEntry;

      function addEntry() {
        var length = m.entries.length;
        m.entries.unshift({index: length});
      }

      function deleteEntry(entry) {
        utils.remove(m.entries, entry);
      }
    }
  }
})();
