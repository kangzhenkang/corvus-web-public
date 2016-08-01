(function() {
  'use strict';

  angular
    .module('corvus')
    .directive('cvScroll', cvScroll);

  /* @ngInject */
  function cvScroll() {
    var directive = {
      link: link,
      restrict: 'A',
      scope: {
        cvScroll: '&',
      }
    };
    return directive;

    function link(scope, element) {
      var content = element.children();
      element[0].isScrollingViewport = true;
      element.bind('scroll', function() {
        var x = element[0].getClientRects()[0];
        var y = content[0].getClientRects()[0];

        scope.cvScroll({
          reachBottom: y.bottom - x.bottom <= 0.01 * x.height,
        });
      });
    }
  }
})();
