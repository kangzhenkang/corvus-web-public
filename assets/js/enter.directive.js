(function() {
  'use strict';

  angular
    .module('corvus')
    .directive('cvEnter', cvEnter);

  /* @ngInject */
  function cvEnter() {
    var directive =  {
      link: link,
      restrict: 'A',
      scope: {
        cvEnter: '&',
      },
    };
    return directive;

    function link(scope, element) {
      element.bind('keydown', function(event) {
        if (event.which == 13) {
          scope.cvEnter();
        }
      });
    }
  }
})();
