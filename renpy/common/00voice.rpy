﻿# Copyright 2004-2016 Tom Rothamel <pytom@bishoujo.us>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# This extra contains a basic implementation of voice support. Right
# now, voice is given its own toggle, and can either be turned on or
# turned off. In the future, we'll probably provide some way of
# toggling it on or off for individual characters.
#
# To use it, place a voice "<sndfile>" line before each voiced line of
# dialogue.
#
#     voice "e_1001.ogg"
#     e "Voice support lets you add the spoken word to your games."
#
# Normally, a voice is cancelled at the start of the next
# interaction. If you want a voice to span interactions, call
# voice_sustain.
#
#     voice "e_1002.ogg"
#     e "Voice sustain is a technique that allows the same voice file.."
#
#     $ voice_sustain()
#     e "...to play for two lines of dialogue."

init -1500 python:

    _voice = object()
    _voice.play = None
    _voice.sustain = False
    _voice.seen_in_lint = False
    _voice.tag = None
    _voice.tlid = None
    _voice.auto_file = None
    _voice.info = None

    # If true, the voice system ignores the interaction.
    _voice.ignore_interaction = False

    # The voice filename format. This may contain the voice tag
    config.voice_filename_format = "{filename}"

    # This is formatted with {id} to produce a filename. If the filename
    # exists, it's played as a voice file.
    config.auto_voice = None

    # Call this to specify the voice file that will be played for
    # the user. This peice only gathers the information so
    # voice_interact can play the right file.
    def voice(filename, tag=None):
        """
        :doc: voice

        Plays `filename` on the voice channel. The equivalent of the voice
        statement.

        `filename`
            The filename to play. This is used with
            :var:`config.voice_filename_format` to produce the
            filename that will be played.

        `tag`
            If this is not None, it should be a string giving a
            voice tag to be played. If None, this takes its
            default value from the voice_tag of the Character
            that causes the next interaction.

            The voice tag is used to specify which character is
            speaking, to allow a user to mute or unmute the
            voices of particular characters.
        """

        if not config.has_voice:
            return

        fn = config.voice_filename_format.format(filename=filename)
        _voice.play = fn
        _voice.tag = tag


    # Call this to specify that the currently playing voice file
    # should be sustained through the current interaction.
    def voice_sustain(ignored="", **kwargs):
        """
        :doc: voice

        The equivalent of the voice sustain statement.
        """

        if not config.has_voice:
            return

        _voice.sustain = True

    # Call this to replay the last bit of voice.
    def voice_replay():
        """
        :doc: voice

        Replays the current voice, if possible.
        """

        if _last_voice_play is not None:
            renpy.sound.play(_last_voice_play, channel="voice")

    # Returns true if we can replay the voice.
    def voice_can_replay():
        """
        :doc: voice

        Returns true if it's possible to replay the current voice.
        """

        return _last_voice_play is not None

    @renpy.pure
    class SetVoiceMute(Action, DictEquality):
        """
        :doc: voice_action

        If `mute` is true, mutes voices that are played with the given
        `voice_tag`. If `mute` is false, unmutes voices that are played
        with `voice_tag`.
        """

        def __init__(self, voice_tag, mute):
            self.voice_tag = voice_tag
            self.mute = mute

        def get_selected(self):
            if self.mute:
                return self.voice_tag in persistent._voice_mute
            else:
                return self.voice_tag not in persistent._voice_mute

        def __call__(self):
            if self.mute:
                persistent._voice_mute.add(self.voice_tag)
            else:
                persistent._voice_mute.discard(self.voice_tag)

            renpy.restart_interaction()

    @renpy.pure
    def SetCharacterVolume(voice_tag, volume=None):
        """
        :doc: voice_action

        This allows the volume of each characters to be adjusted.
        If `volume` is None, this returns the value of volume of `voice_tag`.
        Otherwise, this set it to `volume`.

        `volume` is a number between 0.0 and 1.0, and is interpreted as a
        fraction of the mixer volume for `voice` channel.
        """

        if voice_tag not in persistent._character_volume:
            persistent._character_volume[voice_tag] = 1.0

        if volume is None:
            return DictValue(persistent._character_volume, voice_tag, 1.0)
        else:
            return SetDict(persistent._character_volume, voice_tag, volume)

    @renpy.pure
    class PlayCharacterVoice(Action):
        """
        :doc: voice_action

        This plays `sample` on the voice channel, as if said by a
        character with `voice_tag`.

        `sample`
            The full path to a sound file. No voice-related handling
            of this file is done.
        """

        def __init__(self, voice_tag, sample):
            self.voice_tag = voice_tag
            self.sample = sample

        def __call__(self):
            if self.voice_tag in persistent._voice_mute:
                return

            volume = persistent._character_volume.get(self.voice_tag, 1.0)
            renpy.music.get_channel("voice").set_volume(volume)

            renpy.sound.play(self.sample, channel="voice")

    @renpy.pure
    class ToggleVoiceMute(Action, DictEquality):
        """
        :doc: voice_action

        Toggles the muting of `voice_tag`. This is selected if
        the given voice tag is muted, unless `invert` is true,
        in which case it's selected if the voice is unmuted.
        """

        def __init__(self, voice_tag, invert=False):
            self.voice_tag = voice_tag
            self.invert = invert


        def get_selected(self):
            rv = self.voice_tag in persistent._voice_mute

            if self.invert:
                return not rv
            else:
                return rv

        def __call__(self):
            if self.voice_tag not in persistent._voice_mute:
                persistent._voice_mute.add(self.voice_tag)
            else:
                persistent._voice_mute.discard(self.voice_tag)

            renpy.restart_interaction()

    @renpy.pure
    class VoiceReplay(Action, DictEquality):
        """
        :doc: voice_action

        Replays the most recently played voice.
        """

        def __call__(self):
            voice_replay()

        def get_sensitive(self):
            return voice_can_replay()


    class VoiceInfo(_object):
        """
        An object returned by VoiceInfo and get_voice_info().
        """

        def __init__(self):

            self.filename = _voice.play
            self.auto_filename = None
            self.tlid = None
            self.sustain = _voice.sustain
            self.tag = _voice.tag

            if not self.filename and config.auto_voice:
                tlid = renpy.game.context().translate_identifier

                if tlid is not None:

                    if isinstance(config.auto_voice, (str, unicode)):
                        fn = config.auto_voice.format(id=tlid)
                    else:
                        fn = config.auto_voice(tlid)

                    _voice.auto_filename = fn

                    if fn and renpy.loadable(fn):

                        if _voice.tlid == tlid:
                            self.sustain = True
                        else:
                            self.filename = fn

                self.tlid = tlid

    def _get_voice_info():
        """
        :doc: voice

        Returns information about the voice being played by the current
        say statement. This function may only be called while a say statement
        is executing.

        The object returned has the following fields:

        .. attribute:: VoiceInfo.filename

            The filename of the voice to be played, or None if no files
            should be played.

        .. attribute:: VoiceInfo.auto_filename

            The filename that Ren'Py looked in for automatic-voicing
            purposes, or None if one could not be found.

        .. attribute:: VoiceInfo.tag

            The voice_tag parameter supplied to the speaking Character.
        """

        vi = VoiceInfo()

        if _voice.info is None:
            return vi
        elif _voice.info.tlid == vi.tlid:
            return _voice.info
        else:
            return vi

    def _voice_history_callback(h):
        h.voice = _get_voice_info()

    config.history_callbacks.append(_voice_history_callback)


init -1500 python hide:

    # basics: True if the game will have voice.
    config.has_voice = True

    # The set of voice tags that are currently muted.
    if persistent._voice_mute is None:
        persistent._voice_mute = set()

    # The dictionary of the volume of each voice tags.
    if persistent._character_volume is None:
        persistent._character_volume = dict()

    # This is called on each interaction, to ensure that the
    # appropriate voice file is played for the user.
    def voice_interact():

        if not config.has_voice:
            return

        if _voice.ignore_interaction:
            return

        if renpy.get_mode() == "with":
            return

        vi = VoiceInfo()
        if not _voice.sustain:
            _voice.info = vi

        _voice.play = vi.filename
        _voice.auto_file = vi.auto_filename
        _voice.sustain = vi.sustain
        _voice.tlid = vi.tlid

        volume = persistent._character_volume.get(_voice.tag, 1.0)

        if (not volume) or (_voice.tag in persistent._voice_mute):
            renpy.sound.stop(channel="voice")
            store._last_voice_play = _voice.play

        elif _voice.play:
            if not config.skipping:
                renpy.music.get_channel("voice").set_volume(volume)
                renpy.sound.play(_voice.play, channel="voice")

            store._last_voice_play = _voice.play

        elif not _voice.sustain:
            renpy.sound.stop(channel="voice")
            store._last_voice_play = None

        _voice.play = None
        _voice.sustain = False
        _voice.tag = None

        if _preferences.voice_sustain:
            _voice.sustain = True

    config.start_interact_callbacks.append(voice_interact)
    config.say_sustain_callbacks.append(voice_sustain)

    def voice_afm_callback():
        if _preferences.wait_voice:
            return not renpy.sound.is_playing(channel="voice")
        else:
            return True

    config.afm_callback = voice_afm_callback

    def voice_tag_callback(voice_tag):

        if _voice.tag is None:
            _voice.tag = voice_tag

    config.voice_tag_callback = voice_tag_callback


screen _auto_voice:

    if _voice.auto_file:

        if renpy.loadable(_voice.auto_file):
            $ color = "#ffffff"
        else:
            $ color = "#ffcccc"

        frame:
            xalign 0.5
            yalign 0.0
            xpadding 5
            ypadding 5
            background "#0004"

            text "auto voice: [_voice.auto_file!sq]":
                color color
                size 12

python early hide:

    def parse_voice(l):
        fn = l.simple_expression()
        if fn is None:
            renpy.error('expected simple expression (string)')

        if not l.eol():
            renpy.error('expected end of line')

        return fn

    def execute_voice(fn):
        fn = eval(fn)
        voice(fn)

    def lint_voice(fn):
        _voice.seen_in_lint = True

        fn = _try_eval(fn, 'voice filename')
        if not isinstance(fn, basestring):
            return

        try:
            fn = config.voice_filename_format.format(filename=fn)
        except:
            return

        if not renpy.loadable(fn):
            renpy.error('voice file %r is not loadable' % fn)

    renpy.statements.register('voice',
                              parse=parse_voice,
                              execute=execute_voice,
                              lint=lint_voice,
                              translatable=True)

    def parse_voice_sustain(l):
        if not l.eol():
            renpy.error('expected end of line')

        return None

    def execute_voice_sustain(parsed):
        voice_sustain()

    renpy.statements.register('voice sustain',
                              parse=parse_voice_sustain,
                              execute=execute_voice_sustain,
                              translatable=True)
