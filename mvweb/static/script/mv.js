window.addEventListener('load', function() {
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