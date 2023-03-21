window.addEventListener('DOMContentLoaded', function() {
    let forms = document.getElementsByClassName('skipEmptyFields');
    for (let form of forms) {
      form.addEventListener('formdata', function(event) {
        let formData = event.formData;
        for (let [name, value] of Array.from(formData.entries())) {
          if (value === '') formData.delete(name);
        }
      });
    }
  });

(() => {
  document.addEventListener("DOMContentLoaded", () => {
      const corpChecks = document.querySelectorAll('.corpstat');
      corpChecks.forEach(corpCheck => {
          corpCheck.addEventListener('mouseover', event => {
              if (corpCheck !== event.target) return;
              let tipDiv = event.target.querySelector('.corptooltip');
              tipDiv.dataset.moused = '1';
              if (tipDiv.innerHTML.trim() == '') {
                let corp = event.target.querySelector('.corplink').innerHTML.trim();
                let sessionCheck = sessionStorage.getItem('corp-' + corp)
                if (sessionCheck === null) {
                  let xhr = new XMLHttpRequest();
                  xhr.onreadystatechange = function() {
                      if (xhr.readyState == XMLHttpRequest.DONE) {
                              xresp = xhr.responseText;
                              if (xresp != 'n/a') {
                                  xresp += '% snuggly';
                              }
                              sessionStorage.setItem('corp-' + corp, xresp)
                              tipDiv.innerHTML = sessionStorage.getItem('corp-' + corp)
                              if (tipDiv.dataset.moused === '1') {
                                tipDiv.style.display = 'block';
                              }
                          }
                  }
                  url = '/api/snuggly/corp/' + corp;
                  xhr.responseType = 'text';
                  xhr.open('GET', url);
                  xhr.send();
                } else {
                  tipDiv.innerHTML = sessionStorage.getItem('corp-' + corp)
                  tipDiv.style.display = 'block';
                }
              } else {
                tipDiv.style.display = 'block';
              }
          })
      });
    corpChecks.forEach(corpCheck => {
      corpCheck.addEventListener('mouseleave', event => {
        let tipDiv = event.target.querySelector('.corptooltip');
        tipDiv.dataset.moused = '0';
        tipDiv.style.display = 'none';
      });
    })
  });
})();


(() => {
  document.addEventListener("DOMContentLoaded", () => {
      const pilotChecks = document.querySelectorAll('.pilotstat');
      pilotChecks.forEach(pilotCheck => {
        pilotCheck.addEventListener('mouseover', event => {
              if (pilotCheck !== event.target) return;
              let tipDiv = event.target.querySelector('.pilottooltip');
              tipDiv.dataset.moused = '1';
              if (tipDiv.innerHTML.trim() == '') {
                let corp = event.target.querySelector('.pilotlink').innerHTML.trim();
                let sessionCheck = sessionStorage.getItem('pilot-' + corp)
                if (sessionCheck === null) {
                  let xhr = new XMLHttpRequest();
                  xhr.onreadystatechange = function() {
                      if (xhr.readyState == XMLHttpRequest.DONE) {
                              xresp = xhr.responseText;
                              if (xresp != 'n/a') {
                                  xresp += '% snuggly';
                              }
                              sessionStorage.setItem('pilot-' + corp, xresp)
                              tipDiv.innerHTML = sessionStorage.getItem('pilot-' + corp)
                              if (tipDiv.dataset.moused === '1') {
                                tipDiv.style.display = 'block';
                              }
                          }
                  }
                  url = '/api/snuggly/pilot/' + corp;
                  xhr.responseType = 'text';
                  xhr.open('GET', url);
                  xhr.send();
                } else {
                  tipDiv.innerHTML = sessionStorage.getItem('pilot-' + corp)
                  tipDiv.style.display = 'block';
                }
              } else {
                tipDiv.style.display = 'block';
              }
          })

      });
      pilotChecks.forEach(pilotCheck => {
      pilotCheck.addEventListener('mouseleave', event => {
        let tipDiv = event.target.querySelector('.pilottooltip');
        tipDiv.dataset.moused = '0';
        tipDiv.style.display = 'none';
      });
    })
  });
})();