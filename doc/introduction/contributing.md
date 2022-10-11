# Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit helps, and credit will always be given.

You can contribute in many ways:

## Types of Contributions

### Report Bugs

Report bugs at <https://github.com/openfoodfacts/robotoff/issues>.

If you are reporting a bug, please include:

- Your operating system name and version.
- Any details about your local setup that might be helpful in troubleshooting.
- Detailed steps to reproduce the bug.

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help wanted" is open to whoever wants to implement it. Issues tagged with "good first issue" are suitable for newcomers.

### Implement Features

Look through the GitHub issues for features. Anything tagged with "enhancement" and "help wanted" is open to whoever wants to implement it.

### Write Documentation

Robotoff could always use more documentation, whether as part of the official [Robotoff docs](https://github.com/openfoodfacts/robotoff/tree/master/doc) or in docstrings.

### Submit Feedback

The best way to send feedback is to file an issue at
<https://github.com/openfoodfacts/robotoff/issues>.

If you are proposing a feature:

- Explain in detail how it would work.
- Keep the scope as narrow as possible, to make it easier to implement.
- Remember that this is a volunteer-driven project, and that contributions are welcome.

## Get Started!

Ready to contribute code? Here's how to set up Robotoff for local development.

1.  Fork the robotoff repo on GitHub.
2.  Clone your fork locally:

    ```
    git clone git@github.com:your_name_here/robotoff.git
    ```
3. choose between [docker install (recommended) or local install](../how-to-guides/deployment/dev-install.md) and run it.
   
4. code!

5.  When you're done making changes, check that your changes pass flake8, mypy and the tests. In addition, ensure that your code is formatted using black:

    If you are on Windows, make sure you have [Make for Windows](http://gnuwin32.sourceforge.net/packages/make.htm) installed. Don't forget to add its path in your [system environment variables](https://stackoverflow.com/questions/44272416/how-to-add-a-folder-to-path-environment-variable-in-windows-10-with-screensho/44272417#44272417).

    A sample path may look like this: `C:\Program Files (x86)\GnuWin32\bin`
    
    It is recommended to use Window's default command prompt instead of Power shell for smooth installation.  

    If you are using docker:

    ```
    make lint
    make checks
    make tests
    ```
    To test the APIs on your localhost run 

    ```
    docker-compose up
    ```

    You can make a post request through [Postman](https://www.postman.com/) or simply paste the url in a web browser to make a get request like this one http://localhost:5500/api/v1/insights/

    The mapping of functions and API path is at the end of robotoff/app/api.py

    If you are on a local install:

    ```
    flake8
    black --check .
    mypy .
    isort --check .
    poetry run pytest tests
    ```    

    Before running the test cases make sure you have a database created. Have a look at .env and robotoff/settings.py the default database name, user, and password is

    ```
    postgres
    ```
    Configure them through environment (you may use `.env` if you use docker) as you like. We don't provide sample database as of now but you'll have a database structure ready to start working.

6.  Commit your changes and push your branch to GitHub:

    ```
    git status
    git add files-you-have-modified
    git commit -m "Your detailed description of your changes."
    git push origin name-of-your-bugfix-or-feature
    ```

    In brief, commit messages should follow these conventions:

    > - Always contain a subject line which briefly describes the changes made. For example "Update CONTRIBUTING.rst".
    > - Subject lines should not exceed 50 characters.
    > - The commit body should contain context about the change - how the code worked before, how it works now and why you decided to solve the issue in the way you did.

    More tips at <https://chris.beams.io/posts/git-commit>

7.  Submit a pull request through the GitHub website.

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1.  The pull request should include tests.
2.  If the pull request adds functionality, the docs should be updated. Put your new functionality into a function with a docstring.
3.  The pull request should work for Python 3.7 and above. Check <https://github.com/openfoodfacts/robotoff/actions> and make sure that the tests pass for all supported Python versions.

This contributing page was adapted from [Pyswarms documentation](https://github.com/ljvmiranda921/pyswarms/blob/master/CONTRIBUTING.rst).
