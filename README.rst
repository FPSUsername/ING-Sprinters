.. image:: https://www.ingsprinters.nl/v23850/assets/img/logos/ing.svg
   :align: center
   :target: https://ingsprinters.nl/
   :alt: ING Logo

Retrieve stock exchange information from the ING sprinters website

=================
Table of contents
=================

- `Introduction`_

- `Getting started`_

- `Usage`_

  #. `Custom keyboard`_

  #. `Commands`_

  #. `Inline`_

============
Introduction
============

This bot is made to retrieve stock exchange information from the ING sprinters website with a simple command.

================
Getting started
================

Clone the repository with:

.. code:: shell

    $ git clone https://github.com/FPSUsername/ING-Sprinters
    $ cd ING-Sprinters

Create a file named `token.txt` and place your telegram token inside it with:

.. code:: shell

    $ echo 'YOUR_TOKEN' > token.txt

install the required python packages with:

.. code:: shell

    $ pip install -r requirements.txt

Run the bot with:


.. code:: shell

    $ python main.py

That's it!

============
Usage
============

-------------------
Custom keyboard
-------------------

The keyboard has four functions listed below.

.. image:: https://i.imgur.com/F5Eb3P3.png
   :align: center
   :alt: Custom keyboard

^^^^^^^^
Track
^^^^^^^^

After pressing the track button, you'll be greeted by a message asking for any ISIN that's currently available on the website of ING.
Sending an ISIN will add the sprinter to your account's list.

^^^^^^^^
List
^^^^^^^^

The list button simply lists all your added sprinters, showing all the useful information about the sprinter.
It also shows the link to the ISIN and the market itself.
If you have more than 5 sprinters added, the results will be paged.

^^^^^^^^
Remove
^^^^^^^^

In order to remove a sprinter from your list, you can simply tap a sprinter in the shown list after pressing the remove button.

^^^^^^^^
Settings
^^^^^^^^

The settings allow you to display or hide ISIN, Bied, Laat, %1 dag, Hefboom, Stop loss-niveau and Referentie.
By default everything is enabled.

-------------------
Commands
-------------------

With the ``/market`` command, you can immediately see the current value of the market:

``/market AEX``

| **AEX**
| **Referentiekoers** *570,22 +0,71 %*

With the ``/ing`` command, you can immediately see the current data of any sprinter from any market:

``/ing AEX NL0013202294``

| **AEX**
| **Bied** *8,25*
| **Laat** *8,27*
| **% 1 dag** *5,22 %*
| **Hefboom** *6,9*
| **Stop loss-niveau** *489,00*
| **Referentiekoers** *570,22 +0,71 %*

-------------------
Inline
-------------------

The inline is used to find a market and/or sprinter. Simply type ``@mybot a`` following by any letter. This will show a list of all markets starting wit ``a``.
If you select the result, it will automatically trigger the ``/market`` command.

Type the whole market name and a new inline will show with ``Short`` and ``Long``. This will filter out the sprinters you wish to see.

If you typed ``Short`` or ``Long``, you can type the sprinter name, ISIN or the value:

.. code:: shell

    @mybot AEX Long Sprinter ...
    @mybot AEX Long 550
    @mybot AEX Long NL00...

Select the sprinter that you want and it will trigger the ``/ing`` command.
